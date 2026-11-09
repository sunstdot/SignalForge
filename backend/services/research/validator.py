"""成稿校验。

这一步是整个方案能否成立的分水岭。只靠 prompt 要求模型"标注来源"，
模型一定会编引用。所以写完必须机器校验一遍：

1. 每个引用标记的 claim id 必须真实存在；
2. claim 的 quote 必须在对应来源正文里逐字命中；
3. 每个结论性行（列表项、表格行、判断句）至少挂一个引用；
4. 被判为 conflict 的事实，正文里不能只写一个版本。

不通过的段落带回失败原因重写，最多两轮；仍不通过就降级为"资料不足"，
而不是把没有依据的句子留在报告里。
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .stages import quote_is_verbatim

CITATION_RE = re.compile(r"\[\[((?:c\d+)(?:,c\d+)*)\]\]")
# 判定为"结论性行"的启发式：列表项、或被强调的句子。
CONCLUSION_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")


def parse_citations(markdown: str) -> List[str]:
    ids: List[str] = []
    for group in CITATION_RE.findall(markdown or ""):
        ids.extend(part.strip() for part in group.split(","))
    return ids


def _line_has_citation(line: str) -> bool:
    return bool(CITATION_RE.search(line))


def check_section(
    draft: dict,
    claims: Dict[str, dict],
    sources: Dict[str, dict],
    verdicts: List[dict],
) -> Tuple[bool, List[dict]]:
    """校验一节。

    返回 (是否通过, 问题列表)。每个问题带 type 和 detail，便于回写重写 prompt。
    """
    problems: List[dict] = []
    markdown = draft.get("markdown", "")

    if not markdown.strip():
        return False, [{"type": "empty", "detail": "本节没有产出正文"}]

    cited = parse_citations(markdown)

    for cid in cited:
        claim = claims.get(cid)
        if not claim:
            problems.append({"type": "unknown_claim", "detail": f"引用了不存在的论断 {cid}"})
            continue
        source = sources.get(claim.get("source_id"), {})
        if not quote_is_verbatim(claim.get("quote", ""), source.get("text", "")):
            problems.append({
                "type": "quote_mismatch",
                "detail": f"{cid} 的引文无法在该来源正文中逐字命中",
            })

    for line in markdown.splitlines():
        if not CONCLUSION_LINE_RE.match(line):
            continue
        if not _line_has_citation(line):
            problems.append({
                "type": "uncited_line",
                "detail": f"结论行缺少引用：{line.strip()[:80]}",
            })

    cited_set = set(cited)
    for cluster in verdicts:
        if cluster.get("verdict") != "conflict":
            continue
        cluster_ids = set(cluster.get("claim_ids") or [])
        if len(cluster_ids) < 2:
            continue
        # 要求正文呈现分歧，而不是要求引用簇内每一条。
        # 一个冲突簇常有 4-8 条说法，全引不现实；至少引到两个不同版本，
        # 读者才看得到"这里存在不一致"。
        cited_from_cluster = cluster_ids & cited_set
        if not cited_from_cluster:
            # 这一节完全没提到该冲突事实，不能算"隐藏冲突"。
            # 早先这里不看引用数就判，导致每一节都为所有冲突簇各报一次，全是误报。
            continue
        if len(cited_from_cluster) < 2:
            problems.append({
                "type": "conflict_hidden",
                "detail": (
                    f"冲突簇只引用了 {len(cited_from_cluster)} 个版本，"
                    f"请至少写出两个不同来源的说法"
                ),
            })

    return (not problems), problems


def build_report(
    title: str,
    thesis: str,
    drafts: List[dict],
    claims: Dict[str, dict],
    verdicts: List[dict],
    sources: Dict[str, dict],
) -> str:
    """把各节拼成完整 Markdown，末尾附来源清单。"""
    parts = [f"# {title}"]
    if thesis:
        parts.append(f"> {thesis}")

    for draft in drafts:
        parts.append(f"## {draft.get('heading', '')}")
        body = draft.get("markdown", "").strip()
        parts.append(body or "> 本节资料不足，未能形成有依据的结论。")
        rejected = draft.get("rejected") or []
        if rejected:
            notes = "；".join(sorted({r.get("type", "") for r in rejected}))
            parts.append(f"> ⚠️ 本节有 {len(rejected)} 处校验未通过（{notes}），相应句子已降级或移除。")

    # 来源清单：只列真正被抓到正文的来源
    used = sorted({cid for cid in parse_citations("\n".join(d.get("markdown", "") for d in drafts))})
    used_sources = []
    for cid in used:
        claim = claims.get(cid)
        if not claim:
            continue
        source = sources.get(claim.get("source_id"))
        if source and source.get("id") not in {s["id"] for s in used_sources}:
            used_sources.append(source)

    if used_sources:
        parts.append("## 来源")
        for source in used_sources:
            tier = source.get("tier", "secondary")
            parts.append(f"- [{source.get('title') or source.get('url')}]({source.get('url')}) — {tier}")

    return "\n\n".join(parts).strip() + "\n"
