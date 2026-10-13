"""Daily event selection and independently cached public discussion verification."""
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .event_selector import EVENT_DIR, _write_json, select_events
from .event_search import verify_event
from .llm_client import chat
from .storage import _load_content_file, load_quick_reads


def load_event_radar(day: str, *, cache_dir: Path = EVENT_DIR) -> dict:
    path = cache_dir / f'{day}.json'
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            return {}
    return {}


async def run_event_radar(day: str, *, cache_dir: Path = EVENT_DIR,
                          client: httpx.AsyncClient | None = None,
                          ask=chat, today: str | None = None) -> dict:
    """Historical runs only read disk; model and public searches happen during today's daily run."""
    if day != (today or datetime.now().strftime('%Y-%m-%d')):
        return load_event_radar(day, cache_dir=cache_dir)
    events = select_events(day, _load_content_file(day), load_quick_reads(day),
                           cache_dir=cache_dir, ask=ask)
    async def verify(using_client):
        selected = []
        reddit_limited = False
        for event in events:
            try:
                discussion = await verify_event(
                    using_client, event, day, cache_dir=cache_dir,
                    skip_platforms={'reddit'} if reddit_limited else set(),
                )
            except Exception:
                discussion = {name: {'status': 'unavailable', 'posts': []}
                              for name in ('x', 'hn', 'reddit')}
            if discussion['reddit'].get('reason') == 'rate_limited':
                reddit_limited = True
            selected.append({**event, 'discussions': discussion})
        return selected
    if events:
        if client is None:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as owned:
                selected = await verify(owned)
        else:
            selected = await verify(client)
    else:
        selected = []
    selection_path = cache_dir / f'{day}.selection.json'
    try:
        selection_status = json.loads(selection_path.read_text(encoding='utf-8'))['status']
    except (OSError, ValueError, KeyError):
        selection_status = 'unavailable'
    result = {'date': day, 'events': selected, 'selection_status': selection_status,
              'checked_at': datetime.now(timezone.utc).isoformat()}
    _write_json(cache_dir / f'{day}.json', result)
    return result
