"""调研流水线的 LLM 阶段：plan / extract / verify / synthesize。

原则：
- 每个阶段只做一件事，输出严格 JSON，由调用方决定是否采纳。
- 抽出来的每条 claim 必须带 quote，且 quote 要在原文里逐字命中；
  这是"可回查"的唯一保证，也是后面 validator 能驳回的依据。
- 失败不抛给用户，返回结构化错误，让流水线把这一阶段标成需要重试，
  而不是让整个 run 静默产出半成品。
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Dict, List, Optional

from ..llm_client import chat_async
from . import clustering, models

MAX_TEXT_PER_SOURCE = 12_000
# 核验按簇并发。簇之间互相独立，并发能显著压缩这一阶段的耗时；
# 不宜过高，模型侧通常按 QPS 限流。
VERIFY_CONCURRENCY = 4


def _strip_fence(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    return raw.rstrip("`").strip()


def _load_json(raw: str, expect):
    text = _strip_fence(raw)
    match = re.search(r"[\[{]", text)
    if not match:
        raise ValueError(f"响应里没有 JSON：{text[:200]}")
    candidate = text[match.start():]
    data = json.loads(candidate)
    if not isinstance(data, expect):
        raise ValueError(f"期望 {expect.__name__}，得到 {type(data).__name__}")
    return data


# ───────────────────────── plan ─────────────────────────

PLAN_SYSTEM = """你是资深行业研究员。你的任务不是回答问题，而是把一个调研主题拆成可检索的结构。

要求：
- sections：3-6 个章节，每个章节回答一类问题；章节标题用名词短语。
- sub_questions：每个章节下 2-4 个具体子问题，必须是能被公开资料证实或证伪的。
- entities：需要专门去找的实体（公司、人物、产品、项目），不超过 15 个。
- 子问题要落到可检索的粒度，不要写"了解其文化"这种无法验证的问题。

只输出 JSON，不要解释。"""


def _plan_prompt(topic: str, questions: List[str], as_of: str) -> str:
    return f"""调研主题：{topic}
截止日期：{as_of}（只采信这一天之前可确认的事实）

用户想回答的问题：
{chr(10).join('- ' + q for q in questions) or '（未指定，请自行拆解）'}

输出结构：
{{
  "thesis": "一句话说明这份调研要论证什么",
  "sections": [{{"id": "s1", "heading": "章节标题", "purpose": "这一章要回答什么"}}],
  "sub_questions": [{{"id": "q1", "section": "s1", "question": "子问题", "queries": ["检索式1", "检索式2"]}}],
  "entities": ["实体1"]
}}

queries 要求：每个子问题给 2-4 条检索式，覆盖官网/官方公告、一手访谈、英文媒体报道的不同角度。"""


async def plan_research(topic: str, questions: List[str], as_of: str) -> models.Plan:
    raw = await chat_async(
        [{"role": "user", "content": _plan_prompt(topic, questions, as_of)}],
        system_prompt=PLAN_SYSTEM,
    )
    data = _load_json(raw, dict)

    sections = [
        {"id": s.get("id") or f"s{i+1}", "heading": s.get("heading", ""), "purpose": s.get("purpose", "")}
        for i, s in enumerate(data.get("sections", []))
        if s.get("heading")
    ]
    valid_sections = {s["id"] for s in sections}
    sub_questions = [
        models.SubQuestion(
            id=q.get("id") or f"q{i+1}",
            section=q.get("section") if q.get("section") in valid_sections else (sections[0]["id"] if sections else "s1"),
            question=q.get("question", ""),
            queries=[c for c in (q.get("queries") or []) if c],
        )
        for i, q in enumerate(data.get("sub_questions", []))
        if q.get("question")
    ]
    return models.Plan(
        thesis=data.get("thesis", ""),
        sections=sections,
        sub_questions=sub_questions,
        entities=[e for e in (data.get("entities") or []) if e][:15],
    )


# ───────────────────────── extract ─────────────────────────

EXTRACT_SYSTEM = """你是证据抽取器。从给定原文中抽取可以被直接引用的原子事实。

硬性要求：
- quote 必须是原文的逐字片段，不得改写、不得拼接、不得翻译。系统会做字面校验，对不上的会被丢弃。
- 每条 claim 只陈述一个事实，不要把两件事写在一句里。
- subject 是这条事实的主语（实体名），predicate 是一个动词短语，便于把不同来源的同一事实聚类。
- 原文里没有明确支持的内容一律不抽。宁可少抽，不要推测。
- as_of 用原文中该事实的时间点（如 2026-02），没有就留空。

只输出 JSON 数组。"""


def _extract_prompt(source_title: str, text: str, entities: List[str]) -> str:
    focus = f"\n优先关注这些实体：{('、'.join(entities))}" if entities else ""
    return f"""来源标题：{source_title}{focus}

原文：
{text[:MAX_TEXT_PER_SOURCE]}

输出：
[{{"text": "事实陈述", "quote": "原文逐字片段", "subject": "主语", "predicate": "谓词短语", "as_of": "YYYY-MM 或空"}}]"""


async def extract_claims(
    source: dict,
    entities: List[str],
    *,
    start_index: int = 0,
) -> List[models.Claim]:
    text = (source.get("text") or "").strip()
    if not text:
        return []

    raw = await chat_async(
        [{"role": "user", "content": _extract_prompt(source.get("title", ""), text, entities)}],
        system_prompt=EXTRACT_SYSTEM,
    )
    items = _load_json(raw, list)

    claims: List[models.Claim] = []
    for i, item in enumerate(items):
        quote = (item.get("quote") or "").strip()
        claim_text = (item.get("text") or "").strip()
        if not quote or not claim_text:
            continue
        claims.append(
            models.Claim(
                id=f"c{start_index + i + 1}",
                text=claim_text,
                quote=quote,
                source_id=source["id"],
                subject=(item.get("subject") or "").strip(),
                predicate=(item.get("predicate") or "").strip(),
                as_of=(item.get("as_of") or "").strip() or None,
            )
        )
    return claims


def quote_is_verbatim(quote: str, text: str) -> bool:
    """quote 是否能在原文中逐字命中。

    做适度归一化（空白、全半角引号），但不容忍改写——改写过的"引文"
    一旦流到报告里，读者就无法回查。
    """
    if not quote or not text:
        return False

    def norm(value: str) -> str:
        value = value.replace("　", " ")
        value = re.sub(r"[‘’“”]", '"', value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    return norm(quote) in norm(text)


# ───────────────────────── verify ─────────────────────────

VERIFY_SYSTEM = """你是事实核验员。给你一组论断，它们按"同一个实体 + 同一个属性"归到了一簇，但来自不同来源。

要求：
- 判断这些来源是否在说同一件事。
- verdict 判定：
  confirmed——1 个官方来源，或 >=2 个互相独立的媒体/一手来源给出相容的信息
  single——只有 1 个来源真正支持
  conflict——来源之间有不相容的说法（数字不同、时间不同、结论相反）
- 转述同一篇报道不算独立来源，这一点必须在 note 里说明。
- 只要数字或时间不同就算冲突，不要把差异解释成"不同时期的合理变化"。
- 不要因为措辞不同就判为冲突，也不要因为语气一致就判为支持。

只输出 JSON 数组。"""


def _verify_prompt(cluster: dict, claims: Dict[str, dict], sources: Dict[str, dict]) -> str:
    lines = []
    for cid in cluster["claim_ids"][:30]:
        claim = claims.get(cid)
        if not claim:
            continue
        source = sources.get(claim.get("source_id"), {})
        lines.append(
            f"[{cid}] ({source.get('tier', 'secondary')} | {source.get('url', '')[:80]})\n"
            f"  事实：{claim.get('text', '')}\n"
            f"  引文：{claim.get('quote', '')[:300]}"
        )
    return f"""聚类主题：{cluster['key'][0]} / {cluster['key'][1]}
来源数：{len(cluster['source_ids'])}

待核验论断：
{chr(10).join(lines)}

输出：
[{{"claim_ids": ["c1", "c7"], "verdict": "confirmed", "supporters": ["c1", "c7"], "conflicts": [], "note": ""}}]"""


async def verify_cluster(
    cluster: dict,
    claims: Dict[str, dict],
    sources: Dict[str, dict],
) -> List[models.Verdict]:
    """核验一个簇。失败时退化为簇内全部 single，不阻断整体流程。"""
    valid_ids = set(cluster["claim_ids"])
    try:
        raw = await chat_async(
            [{"role": "user", "content": _verify_prompt(cluster, claims, sources)}],
            system_prompt=VERIFY_SYSTEM,
        )
        items = _load_json(raw, list)
    except Exception:
        items = []

    verdicts: List[models.Verdict] = []
    for item in items:
        claim_ids = [cid for cid in item.get("claim_ids", []) if cid in valid_ids]
        if not claim_ids:
            continue
        verdict = item.get("verdict", "single")
        if verdict not in ("confirmed", "single", "conflict"):
            verdict = "single"
        verdicts.append(
            models.Verdict(
                claim_ids=claim_ids,
                verdict=verdict,
                supporters=[c for c in item.get("supporters", []) if c in valid_ids],
                conflicts=[c for c in item.get("conflicts", []) if c in valid_ids],
                note=(item.get("note") or "").strip(),
            )
        )

    covered = {cid for v in verdicts for cid in v.claim_ids}
    for cid in cluster["claim_ids"]:
        if cid not in covered:
            verdicts.append(models.Verdict(claim_ids=[cid], verdict="single", note="未形成一致判断"))
    return verdicts


async def verify_claims(claims: List[dict], sources: Dict[str, dict]) -> List[models.Verdict]:
    """先聚类，只把跨来源的簇送模型核验。

    之前把所有论断塞进一个 prompt，超过 120 条就被截断，剩下的全部兜底成 single
    （实测 2527 条里 2471 条是这么来的，标注实际上是失效的）。改成按簇核验后，
    调用量取决于簇数而不是论断数，单来源的论断也不必再花模型调用。
    """
    if not claims:
        return []

    claim_map = {c["id"]: c for c in claims}
    clusters = clustering.cluster_claims(claims)
    targets = clustering.select_for_verification(clusters)

    semaphore = asyncio.Semaphore(VERIFY_CONCURRENCY)

    async def one(cluster: dict) -> List[models.Verdict]:
        async with semaphore:
            return await verify_cluster(cluster, claim_map, sources)

    results = await asyncio.gather(*(one(c) for c in targets), return_exceptions=True)

    verdicts: List[models.Verdict] = []
    verified_ids: set[str] = set()
    for batch in results:
        if isinstance(batch, list):
            verdicts.extend(batch)
            verified_ids.update(cid for v in batch for cid in v.claim_ids)

    # 没进核验的标 single，并在 note 里说清原因，不伪装成"已核验但只有一源"
    selected_ids = {cid for c in targets for cid in c["claim_ids"]}
    for claim in claims:
        if claim["id"] in verified_ids:
            continue
        note = ("未进入核验（单来源，无可对照的第二方）"
                if claim["id"] not in selected_ids else "未形成一致判断")
        verdicts.append(models.Verdict(claim_ids=[claim["id"]], verdict="single", note=note))
    return verdicts


# ───────────────────────── synthesize ─────────────────────────

SYNTH_SYSTEM = """你是研究报告撰写者。你只能使用给定的论断写正文。

硬性要求：
- 每个结论性句子（markdown 列表项、段落里的判断句）后面必须带引用标记，格式 [[c12]] 或 [[c7,c12]]。
- 标记里的 id 只能来自给定论断列表，不得自造。
- 不同来源对同一事实给出不同数字时，两个数字都写出来并说明分歧，不要挑一个。
- 不允许写论断列表里没有的内容，包括"总体来看""可以推断"这类引申。
- 中文输出，Markdown 格式，不要输出章节标题（外层已经包好）。

只输出这一节的 Markdown 正文。"""


def _synth_prompt(section: dict, verdicts: List[dict], claims: Dict[str, dict], problems: Optional[List[dict]] = None) -> str:
    allowed = []
    for verdict in verdicts:
        for cid in verdict.get("claim_ids", []):
            claim = claims.get(cid)
            if not claim:
                continue
            allowed.append(
                f"[[{cid}]] ({verdict['verdict']}) {claim['text']}\n"
                f"    原文：{claim['quote'][:240]}"
            )

    revision = ""
    if problems:
        lines = "\n".join(f"- [{p.get('type')}] {p.get('detail')}" for p in problems[:15])
        revision = f"""
上一版没有通过校验，请修正这些问题后重写：
{lines}
"""

    return f"""章节：{section.get('heading', '')}
这一章要回答：{section.get('purpose', '')}

可用论断（括号内是核验结论）：
{chr(10).join(allowed) or '（无可用论断，请只写一句说明资料不足）'}
{revision}
请写这一节正文。"""


async def synthesize_section(
    section: dict,
    verdicts: List[dict],
    claims: Dict[str, dict],
    problems: Optional[List[dict]] = None,
) -> models.SectionDraft:
    section_verdicts = [
        v for v in verdicts
        if any(cid in claims and claims[cid].get("section_hint") == section.get("id") for cid in v.get("claim_ids", []))
    ]
    # 没有 section_hint 时退回全量可用论断，由模型自己挑相关部分。
    candidates = section_verdicts or verdicts

    raw = await chat_async(
        [{"role": "user", "content": _synth_prompt(section, candidates, claims, problems)}],
        system_prompt=SYNTH_SYSTEM,
    )
    markdown = _strip_fence(raw)
    return models.SectionDraft(
        section_id=section.get("id", ""),
        heading=section.get("heading", ""),
        markdown=markdown,
        claim_ids=sorted(set(re.findall(r"\[\[(c\d+)(?:,c\d+)*\]\]", markdown))),
    )
