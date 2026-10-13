"""Bounded public discussion lookups; unavailable channels are never empty success."""
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET

from .event_selector import EVENT_DIR, _canonical_url, _write_json


ATOM_NS = {'atom': 'http://www.w3.org/2005/Atom'}


def _empty(status: str) -> dict:
    return {'status': status, 'posts': []}


def _seed_urls(event: dict) -> set[str]:
    urls = {_canonical_url(seed.get('url', '')) for seed in event.get('sources', [])}
    for seed in event.get('sources', []):
        if str(seed.get('id', '')).startswith('hn-'):
            urls.add(_canonical_url(f"https://news.ycombinator.com/item?id={seed['id'][3:]}"))
    return urls


def _hn_hits(payload: dict, event: dict, day: str) -> list[dict]:
    results = []
    seed_urls = _seed_urls(event)
    seed_ids = {str(seed.get('id')) for seed in event.get('sources', [])}
    seed_authors = {seed.get('author') for seed in event.get('sources', [])
                    if seed.get('source') == 'Hacker News' and seed.get('author')}
    for hit in payload['hits'][:10]:
        if not isinstance(hit, dict) or not str(hit.get('objectID', '')).isdigit():
            continue
        ident = str(hit['objectID'])
        link = f'https://news.ycombinator.com/item?id={ident}'
        if f'hn-{ident}' in seed_ids or _canonical_url(link) in seed_urls:
            continue
        if _canonical_url(hit.get('url') or '') in seed_urls or hit.get('author') in seed_authors:
            continue
        title = str(hit.get('title') or hit.get('story_title') or '')
        if event['entity'].casefold() not in title.casefold():
            continue
        published = str(hit.get('created_at') or '')
        try:
            posted = datetime.fromisoformat(published.replace('Z', '+00:00'))
            if posted.tzinfo is None or not date.fromisoformat(day) - timedelta(days=2) <= posted.date() <= date.fromisoformat(day):
                continue
        except ValueError:
            continue
        post = {'url': link, 'title': title, 'author': hit.get('author') or '',
                'published_at': published, 'source': 'Hacker News'}
        points, comments = hit.get('points'), hit.get('num_comments')
        if isinstance(points, int) and isinstance(comments, int):
            post['engagement'] = {'points': points, 'comments': comments}
        results.append(post)
    return results[:5]


def _reddit_entries(root, event: dict, day: str) -> list[dict]:
    results = []
    seed_urls = _seed_urls(event)
    seed_authors = {seed.get('author') for seed in event.get('sources', [])
                    if str(seed.get('source', '')).startswith('r/') and seed.get('author')}
    for entry in root.findall('atom:entry', ATOM_NS)[:10]:
        link = entry.find('atom:link', ATOM_NS)
        url = link.get('href', '') if link is not None else ''
        title = entry.findtext('atom:title', default='', namespaces=ATOM_NS)
        published = entry.findtext('atom:published', default='', namespaces=ATOM_NS)
        author = entry.findtext('atom:author/atom:name', default='', namespaces=ATOM_NS)
        content = entry.findtext('atom:content', default='', namespaces=ATOM_NS)
        body = BeautifulSoup(unescape(content), 'html.parser').get_text(' ', strip=True)
        if not url or urlsplit(url).scheme not in {'http', 'https'} or _canonical_url(url) in seed_urls:
            continue
        if author in seed_authors or event['entity'].casefold() not in f'{title} {body}'.casefold():
            continue
        try:
            posted = datetime.fromisoformat(published.replace('Z', '+00:00'))
            if posted.tzinfo is None or not date.fromisoformat(day) - timedelta(days=2) <= posted.date() <= date.fromisoformat(day):
                continue
        except ValueError:
            continue
        # A repost of the same external article is not independent corroboration.
        html = unescape(content)
        external_urls = [link.get('href', '') for link in BeautifulSoup(html, 'html.parser').find_all('a')]
        if any(_canonical_url(link) in seed_urls for link in external_urls):
            continue
        results.append({'url': url, 'title': title, 'author': author,
                        'published_at': published, 'source': 'Reddit'})
    return results[:5]


async def _query(client: httpx.AsyncClient, event: dict, day: str, platform: str,
                 query: str) -> dict:
    try:
        if platform == 'hn':
            since = int(datetime.combine(date.fromisoformat(day) - timedelta(days=2),
                                         datetime.min.time(), timezone.utc).timestamp())
            response = await client.get('https://hn.algolia.com/api/v1/search_by_date',
                                        params={'query': query, 'tags': 'story', 'hitsPerPage': 10,
                                                'numericFilters': f'created_at_i>{since}'}, timeout=8)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get('hits'), list):
                return _empty('unavailable')
            posts = _hn_hits(payload, event, day)
        else:
            response = await client.get('https://www.reddit.com/search/.rss',
                                        params={'q': query, 'sort': 'new', 't': 'week', 'limit': 10},
                                        headers={'User-Agent': 'SignalForge/0.1 (public event lookup)'}, timeout=8)
            response.raise_for_status()
            if response.url.host != 'www.reddit.com':
                return _empty('unavailable')
            root = ET.fromstring(response.content)
            if root.tag != '{http://www.w3.org/2005/Atom}feed':
                return _empty('unavailable')
            posts = _reddit_entries(root, event, day)
        return {'status': 'found' if posts else 'no_results', 'posts': posts}
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            return {**_empty('unavailable'), 'reason': 'rate_limited'}
        return _empty('unavailable')
    except (httpx.HTTPError, ET.ParseError, ValueError, KeyError, TypeError):
        return _empty('unavailable')


async def verify_event(client: httpx.AsyncClient, event: dict, day: str, *,
                       cache_dir: Path = EVENT_DIR, x_provider=None,
                       skip_platforms: set[str] | None = None) -> dict:
    """Only a confirmed, injected no-auth X provider may change X's default status."""
    result = {'x': _empty('unavailable')}
    if x_provider is not None:
        try:
            result['x'] = await x_provider(client, event, day)
        except Exception:
            result['x'] = _empty('unavailable')
    queries = list(dict.fromkeys(str(q).strip() for q in (event.get('query'), event.get('entity')) if q))[:2]
    for platform in ('hn', 'reddit'):
        if platform in (skip_platforms or set()):
            result[platform] = {**_empty('unavailable'), 'reason': 'rate_limited'}
            continue
        collected = []
        statuses = []
        failure_reason = ''
        for query in queries:
            signature = hashlib.sha256(query.encode()).hexdigest()[:12]
            safe_id = ''.join(c for c in str(event['id']) if c.isalnum() or c == '-')
            path = cache_dir / 'search' / f'{day}-{safe_id}-{platform}-{signature}.json'
            cached = None
            if path.is_file():
                try:
                    cached = json.loads(path.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    pass
            response = cached if cached and cached.get('status') in {'found', 'no_results'} else (
                await _query(client, event, day, platform, query))
            if response['status'] in {'found', 'no_results'} and cached is None:
                _write_json(path, response)
            statuses.append(response['status'])
            failure_reason = response.get('reason', failure_reason)
            collected.extend(response['posts'])
            if collected or response['status'] == 'unavailable':
                break
        if collected:
            # Do not turn a repeated HN/Reddit result into several discussions.
            unique = {post['url']: post for post in collected}
            result[platform] = {'status': 'found', 'posts': list(unique.values())[:5]}
        elif 'unavailable' in statuses:
            result[platform] = _empty('partial' if 'no_results' in statuses else 'unavailable')
            if failure_reason:
                result[platform]['reason'] = failure_reason
        else:
            result[platform] = _empty('no_results' if statuses else 'unavailable')
    return result
