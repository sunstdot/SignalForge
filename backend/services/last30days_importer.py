"""last30days raw v3 markdown → SignalForge content items."""
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional

# raw 平台标记 -> (source_type, 显示名)
PLATFORM_MAP = {
    "reddit": ("reddit", "Reddit"),
    "x": ("x", "X"),
    "hackernews": ("hn", "Hacker News"),
    "youtube": ("youtube", "YouTube"),
    "tiktok": ("tiktok", "TikTok"),
    "instagram": ("instagram", "Instagram"),
}

_TOPIC_RE = re.compile(r"^#\s+last30days[^:]*:\s*(.+?)\s*$")
_RANGE_RE = re.compile(r"Date range:\s*\S+\s+to\s+(\d{4}-\d{2}-\d{2})")
_CLUSTER_RE = re.compile(r"^###\s+\d+\.\s*(.+?)\s*\(score\s+(\d+),")
_ITEM_RE = re.compile(r"^\d+\.\s*\[(\w+)\]\s*(.+?)\s*$")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_URL_RE = re.compile(r"^\s*-\s*URL:\s*(\S+)")
_EVIDENCE_RE = re.compile(r"^\s*-\s*Evidence:\s*(.+?)\s*$")


def _make_id(platform_key: str, url: str, title: str) -> str:
    basis = url or title
    return f"l30-{platform_key}-{hashlib.md5(basis.encode('utf-8')).hexdigest()[:12]}"


def parse_last30days_markdown(text: str) -> List[Dict]:
    """把 raw v3 markdown 解析成 content item 列表。"""
    topic = ""
    fallback_date: Optional[str] = None
    cluster_title = ""
    cluster_score = 0
    cur: Optional[Dict] = None
    items: List[Dict] = []

    def flush() -> None:
        nonlocal cur
        if not cur or (not cur.get("url") and not cur.get("title")):
            cur = None
            return
        platform_key, source_name = PLATFORM_MAP.get(
            cur["platform"], ("social", cur["platform"])
        )
        date = cur.get("date") or fallback_date
        score = min(10, round(cluster_score / 6))
        items.append({
            "id": _make_id(platform_key, cur.get("url", ""), cur["title"]),
            "source": source_name,
            "source_type": platform_key,
            "title": cur["title"],
            "url": cur.get("url", ""),
            "summary": cur.get("evidence", ""),
            "original_content": cur.get("evidence", ""),
            "relevance_score": score,
            "tags": [topic] if topic else [],
            "category": [topic] if topic else [],
            "date": date,
            "created_at": date,
            "metadata": {
                "topic": topic,
                "cluster_title": cluster_title,
                "cluster_score": cluster_score,
                "origin": "last30days",
            },
        })
        cur = None

    for line in text.splitlines():
        m = _TOPIC_RE.match(line)
        if m:
            topic = m.group(1)
            continue
        m = _RANGE_RE.search(line)
        if m:
            fallback_date = m.group(1)
            continue
        m = _CLUSTER_RE.match(line)
        if m:
            flush()
            cluster_title, cluster_score = m.group(1), int(m.group(2))
            continue
        m = _ITEM_RE.match(line)
        if m:
            flush()
            cur = {"platform": m.group(1).lower(), "title": m.group(2)}
            continue
        if cur is None:
            continue
        m = _URL_RE.match(line)
        if m:
            cur["url"] = m.group(1)
            continue
        m = _EVIDENCE_RE.match(line)
        if m:
            cur["evidence"] = m.group(1)
            continue
        if "| score:" in line and "date" not in cur:
            dm = _DATE_RE.search(line)
            if dm:
                cur["date"] = dm.group(1)

    flush()
    return items
