"""参考链接学习：从用户提交的参考信息中提取价值特征，参与后续检索与筛选。

数据模型（文件存储于 data/signal_learning/）：
- references.json：参考样本列表（可修改、停用、撤销）
- preferences.json：由 active 参考样本推导出的偏好快照（可检查、可追溯）

价值特征与主题分离：
- 主题（topic/场景）：回答「关于什么」。
- 价值特征（信息贡献 + 价值原因 + 证据形态）：回答「为什么有价值」。
- 匹配候选时，价值特征权重高于主题关键词，避免「同品牌即相似」。
"""
import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import storage as storage_module
from .llm_client import chat_async


def _learning_dir() -> Path:
    # 动态读取，兼容测试中对 storage.DATA_DIR 的 monkeypatch。
    return storage_module.DATA_DIR / "signal_learning"

CONTRIBUTION_TYPES = {"method", "result", "experience", "limitation", "opinion", "other"}

# 证据形态 -> 用于在候选文本中寻找对应信号的标记（中英文）。
# 原则：用能体现「证据形态」的词/短语；泛化单词（we、step、how to、case）单独出现没有判别性。
EVIDENCE_FORM_MARKERS = {
    "code": ["代码", "源码", "repo", "github", "开源", "示例代码", "复现", "open-source", "open source", "reference implementation", "working demo"],
    "process": ["步骤", "流程", "操作过程", "完整过程", "工作流", "端到端", "pipeline", "workflow", "walkthrough", "step-by-step", "how we built"],
    "benchmark": ["实测", "评测", "基准", "benchmark", "benchmarks", "指标对比", "延迟", "吞吐", "eval", "measured", "latency", "faster", "%"],
    "firsthand": ["我们实践", "第一手", "踩坑", "我们团队", "in production", "postmortem", "lessons learned", "case study", "we built", "we found", "we learned", "our experience"],
    "failure": ["失败", "踩坑", "坑", "翻车", "限制", "局限", "教训", "缺点", "failure", "failures", "went wrong", "pitfall", "pitfalls", "caveat", "limitation", "limitations", "what broke"],
    "cost": ["成本", "价格", "定价", "花费", "费用", "cost", "costs", "pricing", "$", "per token", "预算"],
    "result": ["结果", "效果提升", "降低了", "达成", "转化", "留存", "increased", "reduced by", "improved by", "outcome"],
}

# 用于从 topic/场景/贡献里抽取可检索的实词。
# 泛化的领域词（llm/agent/ai 等）会让任何 AI 内容都「主题相似」，必须剔除。
_TOPIC_NOISE = {
    "一个", "一种", "使用", "这个", "那个", "以及", "通过", "用于", "进行", "可以", "发现", "展示",
    "the", "a", "an", "of", "to", "in", "for", "and", "with", "using", "on", "that",
    "ai", "llm", "llms", "agent", "agents", "人工智能", "大模型", "智能体", "模型", "gpt",
    "claude", "gemini", "openai", "anthropic", "deepseek", "prompt", "rag", "mcp",
}





# ───────────────────────── 文件存储 ─────────────────────────

def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return default
    return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def load_references(cache_dir: Optional[Path] = None) -> List[Dict]:
    directory = cache_dir or _learning_dir()
    return _load_json(directory / "references.json", [])


def save_references(references: List[Dict], cache_dir: Optional[Path] = None) -> None:
    directory = cache_dir or _learning_dir()
    directory.mkdir(parents=True, exist_ok=True)
    _save_json(directory / "references.json", references)


def load_preferences_snapshot(cache_dir: Optional[Path] = None) -> Optional[Dict]:
    directory = cache_dir or _learning_dir()
    return _load_json(directory / "preferences.json", None)


def save_preferences_snapshot(preferences: Dict, cache_dir: Optional[Path] = None) -> None:
    directory = cache_dir or _learning_dir()
    directory.mkdir(parents=True, exist_ok=True)
    _save_json(directory / "preferences.json", preferences)


def get_reference_by_id(reference_id: str, cache_dir: Optional[Path] = None) -> Optional[Dict]:
    for ref in load_references(cache_dir):
        if ref.get("id") == reference_id:
            return ref
    return None


def create_reference_record(url: str, user_reason: str = "", user_wants: str = "",
                            title: str = "", content_snippet: str = "",
                            cache_dir: Optional[Path] = None) -> Dict:
    """创建参考样本记录（未分析）。返回新记录。"""
    references = load_references(cache_dir)
    record = {
        "id": f"ref-{uuid.uuid4().hex[:10]}",
        "url": url,
        "title": title or url,
        "user_reason": (user_reason or "").strip(),
        "user_wants": (user_wants or "").strip(),
        "content_snippet": content_snippet or "",
        "status": "active",  # active | disabled
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_status": "pending",  # pending | complete | partial | fetch_failed
        "analysis": None,
        "feedback": [],  # 反馈记录（符合预期/主题相似/不相关）
        "last_similar": None,  # 最近一次试找结果摘要
    }
    references.append(record)
    save_references(references, cache_dir)
    return record


def update_reference_record(reference_id: str, updates: Dict,
                            cache_dir: Optional[Path] = None) -> Optional[Dict]:
    references = load_references(cache_dir)
    for ref in references:
        if ref.get("id") == reference_id:
            for key, value in updates.items():
                ref[key] = value
            ref["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_references(references, cache_dir)
            return ref
    return None


def set_reference_status(reference_id: str, status: str,
                         cache_dir: Optional[Path] = None) -> Optional[Dict]:
    if status not in {"active", "disabled"}:
        raise ValueError(f"invalid status: {status}")
    return update_reference_record(reference_id, {"status": status}, cache_dir)


# ───────────────────────── 特征提取（纯函数） ─────────────────────────

def split_topic_terms(text: str) -> List[str]:
    """从主题/场景文本中抽取可检索的实词（中文按常见停用词切分，英文按空格）。"""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\s+-]+", " ", str(text).lower())
    tokens = re.split(r"[\s,，、/|]+", cleaned)
    terms = []
    for token in tokens:
        token = token.strip().strip("+-")
        if len(token) < 2 or token in _TOPIC_NOISE:
            continue
        if token not in terms:
            terms.append(token)
    return terms


def match_evidence_forms(text: str, evidence_forms: List[str]) -> Dict[str, List[str]]:
    """在候选文本中查找与参考样本相同的证据形态信号。返回 {form: [命中标记]}。"""
    if not text or not evidence_forms:
        return {}
    lowered = str(text).lower()
    matches: Dict[str, List[str]] = {}
    for form in evidence_forms:
        markers = EVIDENCE_FORM_MARKERS.get(form, [])
        hit = [m for m in markers if m in lowered]
        if hit:
            matches[form] = hit
    return matches


def match_topic_terms(text: str, topic_terms: List[str]) -> List[str]:
    """在候选文本中查找主题实词命中。"""
    if not text or not topic_terms:
        return []
    lowered = str(text).lower()
    return [term for term in topic_terms if term in lowered]


def candidate_value_signal(text: str, evidence_forms: List[str]) -> Dict:
    """候选内容是否具备与参考样本相似的价值特征（不依赖主题关键词）。"""
    return match_evidence_forms(text, evidence_forms)


def score_candidate(item: Dict, reference: Dict) -> Dict:
    """对候选内容打分，区分「主题相似」与「同样有价值」。

    返回可解释的打分结果，不输出无法理解的相似度分数。
    """
    analysis = reference.get("analysis") or {}
    evidence_forms = analysis.get("evidence_forms") or []
    topic_terms = []
    for clue in analysis.get("search_clues") or []:
        topic_terms.extend(split_topic_terms(str(clue.get("query") or "")))
    topic_terms.extend(split_topic_terms(str(analysis.get("topic") or "")))

    text = _candidate_text(item)
    value_match = match_evidence_forms(text, evidence_forms)
    topic_match = match_topic_terms(text, topic_terms)

    # 价值特征命中优先于主题命中；主题命中单独标注，不冒充价值。
    value_score = len(value_match)
    topic_score = len(topic_match)
    return {
        "item_id": item.get("id", ""),
        "value_matches": value_match,
        "topic_matches": topic_match,
        "value_score": value_score,
        "topic_score": topic_score,
        "similarity": "value" if value_score >= 1 else ("topic" if topic_score >= 1 else "none"),
        "reason_parts": [],
    }


def _candidate_text(item: Dict) -> str:
    parts = [
        str(item.get("title") or ""),
        str(item.get("summary") or ""),
        str(item.get("original_content") or ""),
    ]
    comments = (item.get("metadata") or {}).get("comments") or []
    if isinstance(comments, list):
        parts.extend(str(c) for c in comments)
    return " ".join(parts)


def recommendation_reason(score: Dict, reference: Dict) -> str:
    """生成人可读的推荐原因：说明与哪条参考信息相似、相似在哪。"""
    ref_title = reference.get("title") or reference.get("url") or "你提供的参考信息"
    analysis = reference.get("analysis") or {}
    evidence_forms = analysis.get("evidence_forms") or []
    label = {"process": "完整过程", "failure": "失败/限制", "cost": "成本信息",
             "benchmark": "实测数据", "code": "代码/开源", "firsthand": "第一手实践",
             "result": "具体结果"}

    if score.get("similarity") == "value":
        matched_forms = [f for f in score.get("value_matches", {}) if score["value_matches"][f]]
        form_desc = "、".join(label.get(f, f) for f in matched_forms) or "价值特征"
        return f"因你提供的参考信息「{ref_title[:40]}」而推荐：同样包含{form_desc}（价值相似）"
    if score.get("similarity") == "topic":
        terms = score.get("topic_matches", [])[:3]
        return f"因你提供的参考信息「{ref_title[:40]}」而推荐：主题相似（{('、'.join(terms))[:40]}），但未发现相同的价值特征"
    return ""


def rank_candidates(candidates: List[Dict], reference: Dict, limit: int = 3) -> List[Dict]:
    """按「价值相似优先、主题相似次之」排序，并附可解释原因。"""
    scored = []
    for item in candidates:
        score = score_candidate(item, reference)
        if score["similarity"] == "none":
            continue
        score["reason_parts"] = [recommendation_reason(score, reference)]
        scored.append((item, score))
    scored.sort(key=lambda pair: (-pair[1]["value_score"], -pair[1]["topic_score"]))
    return [
        {**item, "match": score, "recommend_reason": "；".join(score["reason_parts"])}
        for item, score in scored[:limit]
    ]


# ───────────────────────── 偏好聚合 ─────────────────────────

def build_preferences(references: List[Dict]) -> Dict:
    """从 active 参考样本聚合偏好快照；每条偏好记录支持它的样本 id，便于追溯与撤销。"""
    active = [r for r in references if r.get("status") == "active" and (r.get("analysis") or {})]

    search_clues: List[Dict] = []
    value_patterns: Dict[str, Dict] = {}
    themes: Dict[str, Dict] = {}

    for ref in active:
        ref_id = ref.get("id", "")
        analysis = ref.get("analysis") or {}

        topic = str(analysis.get("topic") or "").strip()
        if topic:
            themes.setdefault(topic, {"text": topic, "weight": 0, "refs": []})
            themes[topic]["weight"] += 1
            themes[topic]["refs"].append(ref_id)

        for form in analysis.get("evidence_forms") or []:
            value_patterns.setdefault(form, {"form": form, "weight": 0, "refs": []})
            value_patterns[form]["weight"] += 1
            if ref_id not in value_patterns[form]["refs"]:
                value_patterns[form]["refs"].append(ref_id)

        contribution_type = analysis.get("contribution_type") or ""
        if contribution_type:
            key = f"contribution:{contribution_type}"
            value_patterns.setdefault(key, {"form": key, "weight": 0, "refs": []})
            value_patterns[key]["weight"] += 1
            if ref_id not in value_patterns[key]["refs"]:
                value_patterns[key]["refs"].append(ref_id)

        for clue in analysis.get("search_clues") or []:
            query = str(clue.get("query") or "").strip()
            if not query:
                continue
            existing = next((c for c in search_clues if c.get("query") == query), None)
            if existing:
                existing["weight"] = existing.get("weight", 0) + 1
                if ref_id not in existing.setdefault("refs", []):
                    existing["refs"].append(ref_id)
            else:
                search_clues.append({
                    "query": query,
                    "subreddits": list(clue.get("subreddits") or []),
                    "handles": list(clue.get("handles") or []),
                    "weight": 1,
                    "refs": [ref_id],
                })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_references": [r["id"] for r in active],
        "themes": sorted(themes.values(), key=lambda t: -t["weight"]),
        "value_patterns": sorted(value_patterns.values(), key=lambda v: -v["weight"]),
        "search_clues": sorted(search_clues, key=lambda c: -c["weight"]),
    }


def refresh_preferences(cache_dir: Optional[Path] = None) -> Dict:
    """根据当前 active 参考样本重算偏好并落盘快照。"""
    preferences = build_preferences(load_references(cache_dir))
    save_preferences_snapshot(preferences, cache_dir)
    return preferences


def effective_preferences(cache_dir: Optional[Path] = None) -> Dict:
    """当前生效的偏好：优先读快照；没有快照则现场重算（不落盘）。"""
    snapshot = load_preferences_snapshot(cache_dir)
    if snapshot and snapshot.get("active_references"):
        return snapshot
    return build_preferences(load_references(cache_dir))


def learned_boost(item: Dict, preferences: Dict) -> Dict:
    """候选内容因学习结果获得的关注度提升；返回可追溯的解释。

    只提升关注度，不替代内容质量/证据/上下文判断。
    """
    value_patterns = [p for p in preferences.get("value_patterns", [])
                      if isinstance(p, dict) and not str(p.get("form", "")).startswith("contribution:")]
    if not value_patterns:
        return {"boost": 0.0, "matched_forms": {}, "matched_topics": [], "refs": []}

    text = _candidate_text(item)
    forms = [p.get("form") for p in value_patterns if isinstance(p.get("form"), str)]
    matched = match_evidence_forms(text, forms)

    topics = []
    topic_refs = []
    all_terms = set()
    for theme in preferences.get("themes", []):
        terms = split_topic_terms(str(theme.get("text") or ""))
        all_terms.update(terms)
    topic_hits = match_topic_terms(text, sorted(all_terms))
    if topic_hits:
        topics = topic_hits
        topic_refs = [ref for theme in preferences.get("themes", []) for ref in theme.get("refs", [])]

    refs = []
    for form, _hits in matched.items():
        for pattern in value_patterns:
            if pattern.get("form") == form:
                refs.extend(pattern.get("refs", []))
    refs.extend(topic_refs)

    # 价值特征命中比主题命中更重要；主题命中只能小幅加分。
    boost = 1.5 * len(matched) + 0.3 * min(len(topic_hits), 3)
    return {
        "boost": round(boost, 2),
        "matched_forms": matched,
        "matched_topics": topic_hits,
        "refs": sorted(set(refs)),
    }


# ───────────────────────── 内容获取与分析 ─────────────────────────

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _is_x_url(url: str) -> bool:
    return "x.com/" in url or "twitter.com/" in url


async def fetch_reference_content(url: str) -> Dict:
    """抓取参考链接正文；失败时保留缺失状态，返回 {title, content, fetch_ok, reason}。"""
    import httpx
    from bs4 import BeautifulSoup

    result = {"title": "", "content": "", "fetch_ok": False, "reason": ""}
    if not re.match(r"^https?://", url or ""):
        result["reason"] = "invalid_url"
        return result
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                     headers={"User-Agent": _BROWSER_UA}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                result["reason"] = f"http_{resp.status_code}"
                return result
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            title = soup.title.get_text(strip=True) if soup.title else ""
            text = soup.get_text(separator=" ", strip=True)
            result["title"] = title
            result["content"] = text[:6000]
            result["fetch_ok"] = bool(text.strip())
            if not result["fetch_ok"]:
                result["reason"] = "empty_body"
    except Exception as exc:  # noqa: BLE001
        result["reason"] = type(exc).__name__
    return result


def _parse_analysis_json(raw: str) -> Optional[Dict]:
    raw = re.sub(r"^```[a-z]*\n?", "", str(raw or "").strip()).rstrip("`").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError):
        return None


def build_analysis_prompt(title: str, content: str, user_reason: str, user_wants: str) -> str:
    reason_line = user_reason or "（用户未填写，需系统推测）"
    wants_line = user_wants or "（用户未填写）"
    return f"""你是一个情报偏好学习助手。用户提交了一条参考信息，认为它有价值，希望系统据此持续发现类似信息。

# 参考信息
标题：{title}
用户填写的价值原因：{reason_line}
用户希望继续看到：{wants_line}
正文（可能不完整，缺失时不要补写事实）：
{content or "（正文无法获取）"}

# 任务
从这条信息中提取「价值特征」，用于指导后续检索和筛选。重点不是品牌名/工具名，而是「为什么这条信息有价值」。

请只输出一个 JSON 对象（不要 markdown 代码块），字段如下：
{{
  "topic": "主题：什么技术、工具或问题（20字以内）",
  "scenario": "场景：谁在什么情况下使用（30字以内）",
  "contribution_type": "method|result|experience|limitation|opinion|other 之一",
  "contribution": "信息贡献：这条信息带来了什么具体认识（40字以内）",
  "value_reason": "价值原因：为什么值得用户关注（40字以内）",
  "value_reason_source": "user 或 inferred（用户填写的原因优先）",
  "evidence_forms": ["process","failure","cost","benchmark","code","firsthand","result" 中命中的若干，没有则 []"],
  "search_clues": [{{"query": "用于检索的具体问题表达（含相关术语，中文，20字以内）", "subreddits": ["相关 subreddit 名（可为空数组）"], "handles": ["相关 X handle（可为空数组）"]}}],
  "uncertain": "哪些部分仍然不确定（如正文缺失、来源是转述等）"
}}

要求：
- 用户填写的原因（value_reason_source=user）必须优先于系统推测；系统推测只能用于用户未填写时。
- 正文缺失时，uncertain 必须说明，且不得根据标题补写事实。
- evidence_forms 只使用给定枚举值；subreddits/handles 填裸名称（不带 r/ 或 @）。
- 不要输出任何解释文字。"""


async def analyze_reference_content(title: str, content: str, user_reason: str,
                                    user_wants: str) -> Dict:
    """调用 LLM 提取价值特征；失败时返回缺失状态。"""
    prompt = build_analysis_prompt(title, content, user_reason, user_wants)
    try:
        raw = await chat_async([{"role": "user", "content": prompt}])
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": type(exc).__name__}

    parsed = _parse_analysis_json(raw)
    if not parsed:
        return {"ok": False, "error": "unparseable_llm_output"}

    evidence_forms = [f for f in (parsed.get("evidence_forms") or [])
                      if f in EVIDENCE_FORM_MARKERS]
    # 用户填写的原因优先于系统推测；用户未填写时，即使 LLM 误报 user，也标注为 inferred。
    parsed["value_reason_source"] = "user" if user_reason.strip() else "inferred"
    parsed["evidence_forms"] = evidence_forms
    parsed["search_clues"] = parsed.get("search_clues") or []
    parsed["ok"] = True
    return parsed


# ───────────────────────── 试找类似信息 ─────────────────────────

def _build_search_prompt(query: str, subreddits: List[str], handles: List[str],
                         output_dir: Path) -> str:
    sub_line = f"限定在这些 subreddit 里优先检索：{', '.join(subreddits)}" if subreddits else ""
    handle = handles[0] if handles else None
    handle_line = f"相关 X 账号：{handle}" if handle else ""
    return (
        f"请调用 last30days 技能研究话题「{query}」，我需要结构化数据。\n\n"
        f"{sub_line}\n{handle_line}\n"
        "执行要求：\n"
        "1. 必须真正执行 last30days 脚本（通过 Bash 调用 scripts/last30days.py），不要凭记忆编造。\n"
        "2. 多源检索（Reddit、X、Hacker News、Web），不要只查一个来源。\n"
        f"3. 输出格式：`--emit=json --quick --save-dir={output_dir}`，把 JSON 报告写到该目录。\n"
        "4. 某个来源不可用时在回复里说明原因。\n"
        "5. 完成后给出完整 .json 文件绝对路径。"
    )


L30_SCRIPT = Path.home() / ".agents" / "skills" / "last30days" / "scripts" / "last30days.py"


async def _run_last30days_direct(query: str, subreddits: List[str], handles: List[str],
                                 output_dir: Path) -> List[Dict]:
    """直接执行 last30days 脚本（--emit=json --quick），与 wingsbot 路径同一检索能力。"""
    from .last30days_importer import parse_last30days_json

    if not L30_SCRIPT.is_file():
        raise FileNotFoundError(f"last30days script not found: {L30_SCRIPT}")
    args = ["python3", str(L30_SCRIPT), query, "--emit=json", "--quick",
            f"--save-dir={output_dir}"]
    if subreddits:
        args.append(f"--subreddits={','.join(subreddits)}")
    if handles:
        args.append(f"--x-handle={handles[0]}")
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError("last30days timed out after 180s")
    if proc.returncode != 0:
        raise RuntimeError(f"last30days exited {proc.returncode}: {stderr.decode()[:200]}")
    reports = sorted(output_dir.glob("*.json"))
    if not reports:
        raise RuntimeError("last30days produced no json report")
    return parse_last30days_json(reports[0].read_text(encoding="utf-8"))


async def run_similar_search(query: str, subreddits: List[str] = None,
                             handles: List[str] = None) -> Dict:
    """用参考样本的检索线索做一次有界检索。返回 {status, items, error}。

    优先直接调用 last30days 脚本（有界、可失败）；不可用时回退 wingsbot agent。
    检索失败时返回明确状态，不伪造结果；调用方负责区分「无匹配」与「检索失败」。
    """
    subreddits = subreddits or []
    handles = handles or []
    search_dir = _learning_dir() / "searches" / uuid.uuid4().hex
    search_dir.mkdir(parents=True, exist_ok=True)
    try:
        try:
            items = await _run_last30days_direct(query, subreddits, handles, search_dir)
            return {"status": "ok", "items": items, "error": ""}
        except Exception:
            # 直接脚本不可用（如脚本缺失）时，退回 wingsbot agent 路径。
            items = await _run_search_via_wingsbot(query, subreddits, handles, search_dir)
            return {"status": "ok", "items": items, "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"status": "search_failed", "items": [], "error": str(exc)[:300]}
    finally:
        import shutil
        shutil.rmtree(search_dir, ignore_errors=True)


async def _run_search_via_wingsbot(query: str, subreddits: List[str], handles: List[str],
                                   output_dir: Path) -> List[Dict]:
    from .wingsbot_client import invoke_wingsbot, require_artifact
    from .last30days_importer import parse_last30days_json

    prompt = _build_search_prompt(query, subreddits, handles, output_dir)
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: invoke_wingsbot(
            prompt,
            session_key=f"signalforge:signal-learning:{query[:40]}",
            structured=True,
            required_skill="last30days",
            required_tools=["load_skill", "exec"],
            required_artifact_glob=str(output_dir / "*.json"),
        )
    )
    artifact = require_artifact(result, output_dir)
    return parse_last30days_json(artifact.read_text(encoding="utf-8"))


async def find_similar_for_reference(reference_id: str, limit: int = 3,
                                     search_fn=None,
                                     cache_dir: Optional[Path] = None) -> Dict:
    """处理参考样本后，立即用学到的特征试找类似内容。

    search_fn 可注入（测试用）；默认走 wingsbot last30days 有界检索。
    返回结构区分：样本保存 / 分析 / 学习生效 / 试找结果 / 检索失败。
    """
    reference = get_reference_by_id(reference_id, cache_dir)
    if not reference:
        return {"status": "not_found", "error": "reference not found"}

    analysis = reference.get("analysis") or {}
    if not analysis:
        return {
            "status": "no_analysis",
            "reference": reference,
            "error": "reference has no analysis yet",
        }

    clues = analysis.get("search_clues") or []
    query = (clues[0].get("query") or "").strip() if clues else ""
    if not query:
        return {"status": "no_query", "reference": reference, "error": "no search clue derived"}

    subreddits = list(clues[0].get("subreddits") or [])
    handles = list(clues[0].get("handles") or [])

    if search_fn is not None:
        if asyncio.iscoroutinefunction(search_fn):
            search = await search_fn(query, subreddits, handles)
        else:
            search = search_fn(query, subreddits, handles)
    else:
        search = await run_similar_search(query, subreddits, handles)

    recommendations = rank_candidates(search.get("items", []), reference, limit=limit)
    result = {
        "reference": reference,
        "query": query,
        "subreddits": subreddits,
        "handles": handles,
        "search_status": search.get("status", "search_failed"),
        "search_error": search.get("error", ""),
        "found": len(recommendations),
        "recommendations": recommendations,
    }
    if result["search_status"] == "ok" and not recommendations:
        result["status"] = "no_match"
        # 现有来源覆盖不到时，给出扩源建议，不宣称已完整覆盖。
        result["suggestion"] = (
            "现有检索来源未覆盖到符合价值特征的内容。可尝试：补充更具体的场景词、"
            "扩到相关 subreddit/账号，或补充一条不同形态的参考样本。"
        )
    elif result["search_status"] != "ok":
        result["status"] = result["search_status"]
    else:
        result["status"] = "ok"

    update_reference_record(reference_id, {
        "last_similar": {
            "at": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "search_status": result["search_status"],
            "found": result["found"],
        },
    }, cache_dir)
    return result


def record_feedback(reference_id: str, recommendation_index: int, verdict: str,
                    cache_dir: Optional[Path] = None) -> Optional[Dict]:
    """记录用户对试找结果的反馈；反馈用于修正后续偏好（降低单一主题的过度影响）。"""
    if verdict not in {"matched", "topic_only", "irrelevant"}:
        raise ValueError(f"invalid verdict: {verdict}")
    reference = get_reference_by_id(reference_id, cache_dir)
    if not reference:
        return None
    feedback = reference.get("feedback") or []
    feedback.append({
        "at": datetime.now(timezone.utc).isoformat(),
        "index": recommendation_index,
        "verdict": verdict,
    })
    return update_reference_record(reference_id, {"feedback": feedback}, cache_dir)


# ───────────────────────── 每日采集联动 ─────────────────────────

def learned_watchlist_queries(max_queries: int = 3,
                              cache_dir: Optional[Path] = None) -> List[str]:
    """从生效偏好中提取少量具体检索线索，作为每日采集的追加话题。

    控制范围：最多 max_queries 条，避免每个样本无限扩展请求。
    停用/撤销样本后，这里立即不再返回对应线索。
    """
    preferences = effective_preferences(cache_dir)
    queries = []
    for clue in preferences.get("search_clues", []):
        query = str(clue.get("query") or "").strip()
        if query and query not in queries:
            queries.append(query)
        if len(queries) >= max_queries:
            break
    return queries
