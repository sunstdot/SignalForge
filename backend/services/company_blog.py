"""公司博客分桶和轻量跨博客去重；保留原始条目供查阅。"""
import re
from datetime import date
from typing import Dict, List

COMPANY_SOURCES = {
    "OpenAI Blog", "Google DeepMind Blog", "Google AI Blog",
    "Meta Engineering", "Anthropic Blog", "Anthropic", "Cohere Blog",
}
CORPORATE = (
    "partnership", "partners with", "collaborat", "funding", "welcom",
    "joins", "join ", "hiring", "experts", "policy", "civilian defense",
    "co-creating", "fashion", "economy", "workforce", "skills to",
    "your thoughts on", "easier to explore", "grant", "sponsorship",
)
LAUNCH = ("introducing", "launch", "announc", "now available", "release", "shipping")
TECHNICAL = (
    "cach", "open-sourc", "open sourc", "benchmark", "evaluat", "research",
    "architecture", "engineering", "optimization", "technical", "algorithm",
    "system design", "tool use", "agent", "training", "api", "developer",
)
STOPWORDS = {"introducing", "announcing", "launch", "is", "now", "available", "the", "a", "an", "and", "new", "release"}


def is_company_blog(item: Dict) -> bool:
    return item.get("source") in COMPANY_SOURCES or item.get("source_type") == "anthropic_blog"


def classify_company_blog(item: Dict) -> str:
    """保守识别技术和能力发布；泛泛的官方宣传默认为公司新闻。"""
    title = str(item.get("title") or "").lower()
    if any(term in title for term in CORPORATE):
        return "corporate"
    if item.get("source_type") == "anthropic_blog":
        return "technical"
    if any(term in title for term in LAUNCH):
        return "product_launch"
    if any(term in title for term in TECHNICAL):
        return "technical"
    return "corporate"


def _tokens(title: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", title.lower())) - STOPWORDS


def _same_release_window(a: Dict, b: Dict) -> bool:
    first = a.get("published_date") or a.get("published_at")
    second = b.get("published_date") or b.get("published_at")
    if not first or not second:
        return True  # 同一次采集但缺少发布时间，仍可基于严格的标题一致性折叠
    try:
        return abs((date.fromisoformat(str(first)[:10]) - date.fromisoformat(str(second)[:10])).days) <= 2
    except ValueError:
        return False


def dedup_company_blogs(items: List[Dict]) -> List[Dict]:
    """仅折叠不同公司博客近日报导的同一主题，不丢弃原始记录。"""
    first: Dict[frozenset, List[Dict]] = {}
    for item in items:
        key = frozenset(_tokens(str(item.get("title") or "")))
        if len(key) < 3:
            continue
        previous = next((candidate for candidate in first.get(key, [])
                         if candidate.get("source") != item.get("source")
                         and _same_release_window(candidate, item)), None)
        if previous:
            item["dup_of"] = previous["id"]
        else:
            first.setdefault(key, []).append(item)
    return items


def apply_company_blog_policy(items: List[Dict]) -> List[Dict]:
    """只调整公司博客的展示优先级，其他来源及所有原始内容保持不变。"""
    company_items = [item for item in items if is_company_blog(item)]
    dedup_company_blogs(company_items)
    for item in company_items:
        if "content_bucket" in item:
            continue
        bucket = classify_company_blog(item)
        item["content_bucket"] = bucket
        score = item.get("relevance_score", 0)
        if bucket == "corporate":
            item["relevance_score"] = max(0, score - 4)
        elif bucket == "product_launch":
            item["relevance_score"] = min(10, score + 2)
    return items
