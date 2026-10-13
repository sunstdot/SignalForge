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
