"""从 Anthropic 官方栏目页确定性获取近期技术文章。"""
import hashlib
import re
from datetime import date, datetime, timedelta
from typing import Dict, List
from urllib.parse import urlsplit, urlunsplit

import aiohttp
from bs4 import BeautifulSoup

BASE_URL = "https://www.anthropic.com"
SECTIONS = ("engineering", "research")


def normalize_url(url: str) -> str:
    """归一化 URL，去除追踪参数，供跨源去重使用。"""
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return ""
    if not host:
        return ""
    if port:
        host = f"{host}:{port}"
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/") or "/", "", ""))


def parse_anthropic_articles(html: str, section: str) -> List[Dict]:
    """分别解析 Engineering 列表和 Research publication 列表。"""
    if section not in SECTIONS:
        return []
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen = set()
    for link in soup.select(f'a[href^="/{section}/"]'):
        path = link.get("href", "").split("?", 1)[0]
        if path.count("/") != 2 or path in seen:
            continue  # 排除 /research/team/* 导航等链接
        title = link.select_one("h3" if section == "engineering" else '[class*="PublicationList"][class*="title"]')
        time = link.select_one("time")
        if not title or not time:
            continue
        try:
            value = time.get("datetime") or time.get_text(" ", strip=True)
            published = (date.fromisoformat(value[:10]) if re.match(r"^\d{4}-\d{2}-\d{2}", value)
                         else datetime.strptime(value, "%b %d, %Y").date())
        except (ValueError, TypeError):
            continue
        seen.add(path)
        articles.append({
            "title": title.get_text(" ", strip=True),
            "url": BASE_URL + path,
            "published_at": published.isoformat(),
            "section": section,
        })
    return sorted(articles, key=lambda item: item["published_at"], reverse=True)


async def _fetch_html(url: str) -> str:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as response:
            response.raise_for_status()
            return await response.text()


def _body(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    description = soup.find("meta", attrs={"name": "description"})
    summary = description.get("content", "").strip() if description else ""
    article = soup.select_one("main article") or soup.select_one("main")
    raw = article.get_text(" ", strip=True)[:6000] if article else ""
    return summary, raw


async def fetch_anthropic_technical_articles(target_date: str | None = None) -> List[Dict]:
    """抓取近三天的官方文章；独立栏目失败不影响其他栏目。"""
    target = date.fromisoformat(target_date) if target_date else date.today()
    candidates = []
    for section in SECTIONS:
        try:
            html = await _fetch_html(f"{BASE_URL}/{section}")
            candidates.extend(
                item for item in parse_anthropic_articles(html, section)
                if target - timedelta(days=2) <= date.fromisoformat(item["published_at"]) <= target
            )
        except Exception as exc:
            print(f"  ✗ Anthropic {section} failed: {exc}")

    items = []
    seen = set()
    for article in sorted(candidates, key=lambda item: item["published_at"], reverse=True):
        url = normalize_url(article["url"])
        if url in seen or len(items) >= 5:
            continue
        try:
            summary, raw = _body(await _fetch_html(url))
        except Exception as exc:
            print(f"  ✗ Anthropic article failed ({url}): {exc}")
            continue
        if not raw and not summary:
            continue
        seen.add(url)
        items.append({
            "id": "anthropic-" + hashlib.sha256(url.encode()).hexdigest()[:20],
            "source": "Anthropic",
            "source_type": "anthropic_blog",
            "title": article["title"],
            "url": url,
            "summary": summary or raw[:300],
            "original_content": summary or raw[:500],
            "raw_text": raw or summary,
            "published_at": article["published_at"],
            "published_date": article["published_at"],
            "created_at": target.isoformat(),
            "category": [article["section"].capitalize()],
            "tags": ["anthropic", article["section"]],
            "relevance_score": 8,
        })
    return items
