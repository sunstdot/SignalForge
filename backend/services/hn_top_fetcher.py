"""Bounded collection from Hacker News's native public topstories API."""
import asyncio
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup


HN_API = 'https://hacker-news.firebaseio.com/v0'


async def fetch_hn_top(client: httpx.AsyncClient, day: str, limit: int = 20) -> dict:
    """Return recent top stories and honest top-list/item coverage, without article scraping."""
    today = date.fromisoformat(day)
    try:
        response = await client.get(f'{HN_API}/topstories.json', timeout=8)
        response.raise_for_status()
        ids = response.json()
        if not isinstance(ids, list):
            raise ValueError('invalid HN topstories response')
    except (httpx.HTTPError, ValueError, TypeError):
        return {'status': 'unavailable', 'items': []}

    semaphore = asyncio.Semaphore(4)

    async def load(story_id):
        async with semaphore:
            try:
                response = await client.get(f'{HN_API}/item/{story_id}.json', timeout=8)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError):
                return None

    selected = [story_id for story_id in ids[:max(0, min(limit, 20))]
                if isinstance(story_id, int) and story_id > 0]
    stories = await asyncio.gather(*(load(story_id) for story_id in selected))
    items = []
    partial = len(selected) != len(ids[:max(0, min(limit, 20))])
    checked_at = datetime.now(timezone.utc).isoformat()
    for rank, (story_id, story) in enumerate(zip(selected, stories), 1):
        if not isinstance(story, dict):
            partial = True
            continue
        if story.get('type', 'story') != 'story' or story.get('deleted') or story.get('dead'):
            continue
        try:
            published = datetime.fromtimestamp(story['time'], timezone.utc)
        except (KeyError, ValueError, TypeError, OverflowError):
            partial = True
            continue
        if not today - timedelta(days=2) <= published.date() <= today:
            continue
        title = story.get('title')
        if not isinstance(title, str) or not title.strip():
            partial = True
            continue
        discussion_url = f'https://news.ycombinator.com/item?id={story_id}'
        original_url = story.get('url') or discussion_url
        if urlsplit(str(original_url)).scheme not in {'http', 'https'}:
            original_url = discussion_url
        body = BeautifulSoup(story.get('text') or '', 'html.parser').get_text(' ', strip=True)
        metadata = {
            'origin': 'hn_top', 'story_id': story_id, 'rank': rank,
            'discussion_url': discussion_url, 'author': story.get('by', ''),
            'fetched_at': checked_at, 'source_published_at': published.isoformat(),
        }
        score = story.get('score')
        comments = story.get('descendants')
        if isinstance(score, int) and score >= 0 and isinstance(comments, int) and comments >= 0:
            metadata['volume'] = score + comments
            metadata['engagement'] = f'{score} points, {comments} comments'
        items.append({
            'id': f'hn-{story_id}', 'source': 'Hacker News', 'source_type': 'hn',
            'title': title.strip(), 'url': original_url, 'summary': body[:500],
            'original_content': body, 'published_at': published.isoformat(),
            'created_at': day, 'relevance_score': 8, 'metadata': metadata,
        })
    return {'status': 'partial' if partial else 'ok', 'items': items}
