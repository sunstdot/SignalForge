"""Daily event radar uses one cached batch selection and bounded independent verification."""
import json

import httpx
import pytest

import backend.services.event_radar as radar
from backend.services.event_selector import select_events


@pytest.mark.asyncio
async def test_rerun_uses_cached_selection_and_successful_search(tmp_path, monkeypatch):
    day = '2026-10-13'
    items = [{
        'id': 'blog-1', 'source_type': 'blog', 'source': 'Official blog',
        'title': 'Agent Compiler released', 'url': 'https://example.com/agent-compiler',
        'original_content': 'The Agent Compiler team released new reproducible source code with performance benchmarks.',
        'published_at': f'{day}T10:00:00+00:00', 'created_at': day,
    }]
    monkeypatch.setattr(radar, '_load_content_file', lambda date: items)
    monkeypatch.setattr(radar, 'load_quick_reads', lambda date: {})
    calls = {'model': 0, 'hn': 0, 'reddit': 0}
    def ask(messages):
        calls['model'] += 1
        return json.dumps({'events': [{
            'title': 'Agent Compiler released', 'entity': 'Agent Compiler', 'query': 'Agent Compiler',
            'what_happened': 'Source code and reproducible benchmarks were published.',
            'why_read': 'Provides concrete information for developer adoption.', 'seed_ids': ['blog-1'],
        }]})
    def respond(request):
        if request.url.host == 'hn.algolia.com':
            calls['hn'] += 1
            return httpx.Response(200, json={'hits': []})
        calls['reddit'] += 1
        return httpx.Response(429)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        first = await radar.run_event_radar(day, cache_dir=tmp_path, client=client, ask=ask, today=day)
        second = await radar.run_event_radar(day, cache_dir=tmp_path, client=client, ask=ask, today=day)

    assert calls == {'model': 1, 'hn': 1, 'reddit': 2}
    assert first['events'][0]['discussions']['reddit']['status'] == 'unavailable'
    assert second['events'][0]['discussions']['hn']['status'] == 'no_results'
    assert radar.load_event_radar(day, cache_dir=tmp_path) == second
    assert len(items) == 1  # event selection and verification never remove raw content


@pytest.mark.asyncio
async def test_reddit_rate_limit_in_one_event_stops_other_event_queries_for_that_run(tmp_path, monkeypatch):
    day = '2026-10-13'
    items = [
        {'id': 'blog-1', 'source_type': 'blog', 'source': 'Official', 'title': 'Agent Compiler released',
         'url': 'https://example.com/compiler', 'original_content': 'Agent Compiler has released new benchmark data and its source code today.',
         'published_at': f'{day}T10:00:00+00:00'},
        {'id': 'blog-2', 'source_type': 'blog', 'source': 'Official', 'title': 'Robot Library released',
         'url': 'https://example.com/robot', 'original_content': 'Robot Library has published its interface and details of reproducible experiments.',
         'published_at': f'{day}T10:00:00+00:00'},
    ]
    monkeypatch.setattr(radar, '_load_content_file', lambda date: items)
    monkeypatch.setattr(radar, 'load_quick_reads', lambda date: {})
    def ask(messages):
        return json.dumps({'events': [
            {'title': 'Agent Compiler released', 'entity': 'Agent Compiler', 'query': 'Agent Compiler',
             'what_happened': 'Published compiler source code and benchmarks.',
             'why_read': 'Concrete evidence for adoption decisions.', 'seed_ids': ['blog-1']},
            {'title': 'Robot Library released', 'entity': 'Robot Library', 'query': 'Robot Library',
             'what_happened': 'Published a new reproducible interface.',
             'why_read': 'A concrete library update for developers.', 'seed_ids': ['blog-2']},
        ]})
    calls = {'reddit': 0}
    def respond(request):
        if request.url.host == 'hn.algolia.com':
            return httpx.Response(200, json={'hits': []})
        calls['reddit'] += 1
        return httpx.Response(429)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await radar.run_event_radar(day, cache_dir=tmp_path, client=client, ask=ask, today=day)
    assert len(result['events']) == 2
    assert calls['reddit'] == 1
    assert result['events'][1]['discussions']['reddit']['status'] == 'unavailable'


@pytest.mark.asyncio
async def test_historical_radar_only_reads_saved_state(tmp_path, monkeypatch):
    def unexpected(date):
        raise AssertionError('historical view launched live selection')
    monkeypatch.setattr(radar, '_load_content_file', unexpected)
    assert await radar.run_event_radar('2026-01-01', cache_dir=tmp_path, today='2026-10-13') == {}
