"""Today-only followed X account collection with per-handle coverage and rerun safety."""
import asyncio
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

import httpx

from .storage import DATA_DIR, _load_content_file, store_content_items
from .x_public_profile import HANDLE, fetch_public_profile


ACCOUNT_RUN_DIR = DATA_DIR / 'account_runs'


def load_x_account_day(day: str, *, cache_dir: Path | None = None) -> dict:
    date.fromisoformat(day)
    path = (cache_dir or ACCOUNT_RUN_DIR) / f'{day}.json'
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _save(day: str, data: dict, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f'{day}.json'
    tmp = None
    try:
        with NamedTemporaryFile('w', encoding='utf-8', dir=cache_dir,
                                prefix=f'{day}-', suffix='.tmp', delete=False) as handle:
            tmp = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, target)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _status_key(url: str) -> str:
    """Treat x.com/twitter.com and tracking-parameter variants of a post as one URL."""
    try:
        parts = urlsplit(str(url))
        host = (parts.hostname or '').lower().removeprefix('www.')
        if parts.scheme not in {'http', 'https'}:
            return ''
        if host in {'x.com', 'twitter.com', 'mobile.twitter.com'}:
            match = re.search(r'/status/(\d{15,20})(?:/|$)', parts.path, re.I)
            return f'x-status-{match.group(1)}' if match else ''
        return f'{host}{parts.path.rstrip("/")}' if host else ''
    except ValueError:
        return ''


def _recent_verified(post: dict, handle: str, day: str, lookback_days: int) -> bool:
    metadata = post.get('metadata') or {}
    if metadata.get('origin') != 'x_public_account' or metadata.get('account', '').casefold() != f'@{handle}'.casefold():
        return False
    url = post.get('url', '')
    if not _status_key(url) or urlsplit(url).hostname not in {'x.com', 'twitter.com'}:
        return False
    if post.get('source_type') != 'x' or metadata.get('post_type') not in {'quote', 'original'}:
        return False
    try:
        published = datetime.fromisoformat(str(post['published_at']).replace('Z', '+00:00'))
        if published.tzinfo is None:
            return False
        today = date.fromisoformat(day)
        return today - timedelta(days=lookback_days) <= published.date() <= today
    except (KeyError, TypeError, ValueError):
        return False


async def run_x_account_daily(day: str, handles: list[str], *, cache_dir: Path | None = None,
                              client: httpx.AsyncClient | None = None,
                              today: str | None = None, max_posts_per_account: int = 5,
                              lookback_days: int = 2) -> dict:
    """Only verified public originals/quotes enter content; cache preserves per-account status."""
    date.fromisoformat(day)
    directory = cache_dir or ACCOUNT_RUN_DIR
    if day != (today or date.today().isoformat()):
        return load_x_account_day(day, cache_dir=directory)
    selected = []
    seen_handles = set()
    for value in handles:
        handle = value.lstrip('@') if isinstance(value, str) else ''
        if not HANDLE.fullmatch(handle) or handle.casefold() in seen_handles:
            continue
        selected.append(handle)
        seen_handles.add(handle.casefold())
        if len(selected) == 20:
            break

    existing = load_x_account_day(day, cache_dir=directory).get('accounts', {})
    records = {}
    semaphore = asyncio.Semaphore(2)

    async def fetch_one(using_client, handle):
        key = f'@{handle}'
        if existing.get(key, {}).get('status') in {'partial', 'ok'}:
            return existing[key]
        async with semaphore:
            try:
                result = await fetch_public_profile(using_client, handle, day)
            except Exception as exc:
                result = {'status': 'unavailable', 'posts': [], 'reason': type(exc).__name__,
                          'checked_at': datetime.now(timezone.utc).isoformat()}
        verified = [post for post in result.get('posts', [])
                    if _recent_verified(post, handle, day, lookback_days)]
        return {
            'status': 'partial' if verified and result.get('status') == 'ok' else result.get('status', 'unavailable'),
            'checked_at': result.get('checked_at') or datetime.now(timezone.utc).isoformat(),
            'reason': result.get('reason') or 'coverage_unknown',
            'posts': verified[:max(0, min(max_posts_per_account, 10))],
        }

    if client is None:
        async def isolated_fetch(handle):
            # A public page may set a guest cookie. Never pass it to a second account.
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as isolated:
                return await fetch_one(isolated, handle)
        runs = await asyncio.gather(*(isolated_fetch(handle) for handle in selected))
    else:
        runs = await asyncio.gather(*(fetch_one(client, handle) for handle in selected))
    for handle, result in zip(selected, runs):
        records[f'@{handle}'] = result

    seen_urls = {
        key for age in range(lookback_days + 1)
        for stored in _load_content_file((date.fromisoformat(day) - timedelta(days=age)).isoformat())
        if (key := _status_key(stored.get('url', '')))
    }
    fresh = []
    for record in records.values():
        for post in record['posts']:
            key = _status_key(post['url'])
            if key not in seen_urls:
                fresh.append(post)
                seen_urls.add(key)
    stored_count = store_content_items(fresh) if fresh else 0
    output = {'date': day, 'accounts': records, 'stored_count': stored_count}
    _save(day, output, directory)
    return output
