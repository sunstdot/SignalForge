"""Bounded anonymous subreddit Atom feed discovery with explicit coverage."""
import asyncio
import re
from datetime import date, datetime, timedelta, timezone
from html import unescape
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET


NS = {'atom': 'http://www.w3.org/2005/Atom'}


def _parse_entry(entry, name: str, day: str):
    title = entry.findtext('atom:title', default='', namespaces=NS).strip()
    raw_id = entry.findtext('atom:id', default='', namespaces=NS).strip()
    post_id = raw_id.removeprefix('t3_')
    link = entry.find('atom:link', NS)
    url = link.get('href', '') if link is not None else ''
    raw_date = (entry.findtext('atom:published', default='', namespaces=NS)
                or entry.findtext('atom:updated', default='', namespaces=NS))
    if not (post_id and title and urlsplit(url).scheme in {'http', 'https'} and raw_date):
        return None
    try:
        published = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        if published.tzinfo is None:
            return None
        published = published.astimezone(timezone.utc)
    except ValueError:
        return None
    today = date.fromisoformat(day)
    if not today - timedelta(days=2) <= published.date() <= today:
        return False  # valid but stale, not a feed failure
    content = entry.findtext('atom:content', default='', namespaces=NS)
    body = BeautifulSoup(unescape(content), 'html.parser').get_text(' ', strip=True)[:4000]
    author = entry.findtext('atom:author/atom:name', default='', namespaces=NS)
    return {
        'id': f'reddit-{post_id}', 'source': f'r/{name}', 'source_type': 'reddit',
        'title': title, 'url': url, 'summary': body[:500], 'original_content': body,
        'published_at': published.isoformat(), 'created_at': day, 'relevance_score': 8,
        'metadata': {
            'origin': 'reddit_subreddit', 'subreddit': name, 'author': author,
            'source_published_at': published.isoformat(),
        },
    }


def _extract_comments(payload) -> list[str]:
    """从 reddit comments JSON 中提取有实质内容的回复（有界递归）。"""
    comments: list[str] = []
    if not isinstance(payload, list) or len(payload) < 2:
        return comments

    def walk(node, depth):
        if depth > 3 or len(comments) >= 10:
            return
        if isinstance(node, dict):
            child = node.get("data") or {}
            if node.get("kind") == "t1" and child.get("body"):
                body = " ".join(str(child["body"]).split())
                if len(body) >= 20:
                    comments.append(body[:600])
            replies = child.get("replies")
            if isinstance(replies, dict):
                for c in (replies.get("data") or {}).get("children") or []:
                    walk(c, depth + 1)
        elif isinstance(node, list):
            for c in node:
                walk(c, depth)

    for child in (payload[1].get("data") or {}).get("children") or []:
        walk(child, 1)
    return comments


async def enrich_subreddit_comments(client: httpx.AsyncClient, items: list[dict], *,
                                    max_posts: int = 20, max_comments: int = 5,
                                    pause_seconds: float = 0.5) -> dict:
    """为已采集的 reddit 主帖抓取 top 回复；有界、尽力而为，不因失败丢弃主帖。

    有价值的信息可能在回复中；回复抓取失败时在 metadata 里保留缺失状态。
    """
    statuses: dict = {}
    for item in items[:max_posts]:
        if item.get("source_type") != "reddit" or not str(item.get("id", "")).startswith("reddit-"):
            continue
        post_id = str(item["id"])[len("reddit-"):]
        if not post_id:
            continue
        url = f"https://www.reddit.com/comments/{post_id}.json"
        metadata = item.setdefault("metadata", {})
        try:
            if pause_seconds:
                await asyncio.sleep(pause_seconds)
            response = await client.get(
                url, params={"limit": max(1, min(max_comments, 10)), "depth": 1},
                headers={"User-Agent": "SignalForge/0.1 (public feed)"}, timeout=8)
            response.raise_for_status()
            comments = _extract_comments(response.json())
            metadata["comments"] = comments
            metadata["comments_fetched"] = True
            if not comments:
                metadata["context_missing"] = True
            statuses[item["id"]] = "ok"
        except Exception as exc:  # noqa: BLE001
            metadata["comments_fetched"] = False
            metadata["context_missing"] = True
            statuses[item["id"]] = type(exc).__name__
    return statuses


async def fetch_subreddits(client: httpx.AsyncClient, day: str, names: list[str],
                           max_per_sub: int = 3, *, pause_seconds: float = 1) -> dict:
    """Collect public hot feeds, stopping on a rate limit instead of escalating requests."""
    date.fromisoformat(day)
    items, statuses, errors = [], {}, {}
    requested = 0
    rate_limited = False
    for name in dict.fromkeys(names[:20]):
        label = f'r/{name}'
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,32}', name):
            statuses[label] = 'unavailable'
            errors[label] = 'invalid_name'
            continue
        if rate_limited:
            statuses[label] = 'unavailable'
            errors[label] = 'rate_limited'
            continue
        if requested and pause_seconds:
            await asyncio.sleep(pause_seconds)
        requested += 1
        url = f'https://www.reddit.com/r/{name}/hot/.rss'
        try:
            response = await client.get(url, params={'limit': max(1, min(max_per_sub, 5))},
                                        headers={'User-Agent': 'SignalForge/0.1 (public feed)'}, timeout=8)
            response.raise_for_status()
            if response.url.host != 'www.reddit.com':
                raise ValueError('redirected away from public feed')
            root = ET.fromstring(response.content)
            if root.tag != '{http://www.w3.org/2005/Atom}feed':
                raise ValueError('not an Atom feed')
            partial = False
            for entry in root.findall('atom:entry', NS)[:max(1, min(max_per_sub, 5))]:
                item = _parse_entry(entry, name, day)
                if item is None:
                    partial = True
                elif item is not False:
                    items.append(item)
            statuses[label] = 'partial' if partial else 'ok'
        except httpx.HTTPStatusError as exc:
            statuses[label] = 'unavailable'
            if exc.response.status_code == 429:
                errors[label] = 'rate_limited'
                rate_limited = True
            else:
                errors[label] = f'http_{exc.response.status_code}'
        except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
            statuses[label] = 'unavailable'
            errors[label] = type(exc).__name__
    return {'items': items, 'statuses': statuses, 'errors': errors}
