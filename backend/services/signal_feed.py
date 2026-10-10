"""Phase 1 今日信号：轻量分轨与多源限流，不声称具备趋势聚类能力。"""
import re
from typing import Dict, List

from .company_blog import classify_company_blog, is_company_blog

EXECUTION = {"paper", "arxiv", "repo", "github", "model", "anthropic_blog", "blog"}
INSPIRATION = {"x", "reddit", "hn", "hackernews", "producthunt", "rss", "news",
               "newsletter", "smolai", "wechat", "investor"}
UPSTREAM = {"x", "reddit", "hn", "producthunt"}
GENERIC_FEEDS = {"rss", "news", "newsletter", "wechat", "investor", "smolai", "hackernews", "blog"}
AI_TERMS = re.compile(
    r"\b(?:ai|llm|gpt|claude|gemini|agent|agents|model|models|inference|prompt|"
    r"rag|mcp|openai|anthropic|deepmind|huggingface|neural|machine learning|"
    r"vibe coding|copilot)\b|人工智能|大模型|智能体|模型|提示词|推理|开源",
    re.IGNORECASE,
)


def _track(item: Dict) -> str | None:
    bucket = item.get("content_bucket")
    if not bucket and is_company_blog(item):
        bucket = classify_company_blog(item)
    if bucket == "corporate":
        return None
    if bucket == "product_launch":
        return "inspiration"
    if bucket == "technical":
        return "execution"
    source_type = item.get("source_type")
    if source_type in GENERIC_FEEDS:
        text = f"{item.get('title', '')} {str(item.get('summary') or item.get('original_content') or '')[:300]}"
        if not AI_TERMS.search(text):
            return None
    if source_type in EXECUTION:
        return "execution"
    if source_type in INSPIRATION:
        return "inspiration"
    return None


def _priority(item: Dict) -> float:
    """临时排序规则：现有评分 + 一手来源小幅加成；正式打分留待 Phase 2。"""
    score = float(item.get("relevance_score") or 0)
    if item.get("source_type") in UPSTREAM or item.get("content_bucket") == "product_launch":
        score += 1
    return score


def _card(item: Dict, track: str, quick_reads: Dict) -> Dict:
    cached = quick_reads.get(item.get("id")) or ""
    insight = re.search(r"\*\*值得关注\*\*\s*[：:]\s*(.+)", cached)
    so_what = (insight.group(1).strip() if insight else
               str(item.get("summary") or item.get("original_content") or "").strip()[:160])
    metadata = item.get("metadata") or {}
    evidence = str(metadata.get("engagement") or "").strip()
    if evidence:
        why = f"社区讨论 · {evidence}"
    elif item.get("content_bucket") == "product_launch":
        why = "官方能力发布"
    elif item.get("source_type") in UPSTREAM:
        why = "一手社区信号"
    else:
        why = "技术内容" if track == "execution" else "值得关注"
    return {
        "id": item["id"], "title": item.get("title", ""), "url": item.get("url", ""),
        "source": item.get("source", ""), "source_type": item.get("source_type", ""),
        "published_at": item.get("published_at") or item.get("published_date") or item.get("date"),
        "relevance_score": item.get("relevance_score", 0),
        "track": track, "so_what": so_what, "why": why,
    }


def build_signal_feed(items: List[Dict], quick_reads: Dict | None = None, limit: int = 15) -> Dict:
    """最多返回 limit 条，分轨保底且每个作者/源最多两条；原始内容不变。"""
    feed: Dict = {"inspiration": [], "execution": [], "total": 0}
    if limit <= 0:
        return feed
    tracks = {"inspiration": [], "execution": []}
    for item in items:
        if item.get("dup_of") or not item.get("id"):
            continue
        track = _track(item)
        if track:
            tracks[track].append(item)
    for group in tracks.values():
        group.sort(key=lambda item: (-_priority(item), item.get("id", "")))

    selected: Dict[str, List[Dict]] = {"inspiration": [], "execution": []}
    counts: Dict[str, int] = {}
    seen = set()

    def take(track: str, candidates: List[Dict], max_items: int):
        for item in candidates:
            if len(selected[track]) >= max_items or len(seen) >= limit:
                break
            author = (item.get("metadata") or {}).get("author")
            source = f"{item.get('source_type')}:{author or item.get('source', '')}"
            if item["id"] in seen or counts.get(source, 0) >= 2:
                continue
            selected[track].append(item)
            seen.add(item["id"])
            counts[source] = counts.get(source, 0) + 1

    minimum = min(5, max(1, limit // 3))
    for track in ("inspiration", "execution"):
        take(track, tracks[track], minimum)
    remaining = sorted(
        ((track, item) for track, group in tracks.items() for item in group),
        key=lambda pair: (-_priority(pair[1]), pair[1].get("id", "")),
    )
    for track, item in remaining:
        if len(seen) >= limit:
            break
        take(track, [item], limit)

    for track, group in selected.items():
        feed[track] = [_card(item, track, quick_reads or {}) for item in group]
    feed["total"] = len(seen)
    return feed
