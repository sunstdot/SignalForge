"""Briefing GET consumes saved radar state, never starts research."""
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from main import app
from services import briefing_generator, collector, source_run_store, storage
import services.event_radar as event_radar


@pytest.fixture
def isolated_daily_files(tmp_path, monkeypatch):
    for name in ('content', 'briefings', 'quick_reads', 'source_runs', 'event_radar'):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(storage, 'CONTENT_DIR', tmp_path / 'content')
    monkeypatch.setattr(storage, 'BRIEFINGS_DIR', tmp_path / 'briefings')
    monkeypatch.setattr(storage, 'QUICK_READS_DIR', tmp_path / 'quick_reads')
    monkeypatch.setattr(storage, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(source_run_store, 'SOURCE_RUN_DIR', tmp_path / 'source_runs')
    monkeypatch.setattr(event_radar, 'EVENT_DIR', tmp_path / 'event_radar')
    return tmp_path


def test_saved_event_api_keeps_full_items_and_legacy_tracks(isolated_daily_files, monkeypatch):
    day = '2026-10-13'
    source = {'id': 'blog-1', 'source_type': 'blog', 'source': 'Official',
              'title': 'Agent Compiler released', 'url': 'https://example.com/compiler',
              'summary': 'Public implementation with reproducible benchmarks.',
              'created_at': day, 'published_at': f'{day}T10:00:00+00:00', 'relevance_score': 9}
    storage.store_content_items([source])
    source_run_store.save_source_run(day, {'hn': 'ok', 'reddit': {'r/ClaudeAI': 'unavailable'},
                                           'errors': {'r/ClaudeAI': 'rate_limited'}})
    event = {'id': 'event-1', 'title': 'Agent Compiler released',
             'what_happened': 'Reproducible benchmarks were published.',
             'why_read': 'Developers can examine the actual implementation.',
             'sources': [{'url': source['url'], 'source': 'Official', 'title': source['title']}],
             'discussions': {'x': {'status': 'unavailable', 'posts': []},
                             'hn': {'status': 'found', 'posts': [{
                                 'url': 'https://news.ycombinator.com/item?id=456', 'author': 'reviewer'}]},
                             'reddit': {'status': 'no_results', 'posts': []}}}
    monkeypatch.setattr(briefing_generator, 'load_event_radar',
                        lambda date: {'events': [event], 'selection_status': 'ok'})
    with (patch.object(collector, 'run_event_radar', side_effect=AssertionError('GET started event search')),
          patch.object(collector, 'fetch_hn_top', side_effect=AssertionError('GET started HN'))):
        responses = [TestClient(app).get(f'/api/briefing/{day}') for _ in range(2)]
    assert all(response.status_code == 200 for response in responses)
    payload = responses[0].json()
    assert payload['items'][0]['url'] == source['url']
    assert 'inspiration' in payload['signals'] and 'execution' in payload['signals']
    assert payload['signals']['events'][0]['discussions']['x']['status'] == 'unavailable'
    assert payload['signals']['events'][0]['discussions']['hn']['posts'][0]['author'] == 'reviewer'
    assert payload['signals']['events'][0]['discussions']['reddit']['status'] == 'no_results'
    assert payload['signals']['source_status']['reddit']['r/ClaudeAI'] == 'unavailable'


def test_failed_source_day_is_visible_without_pretending_prior_day_items_are_new(isolated_daily_files):
    day = '2026-10-13'
    storage.store_content_items([{
        'id': 'rss-old', 'title': 'Yesterday story', 'url': 'https://example.com/old',
        'source': 'Official', 'source_type': 'rss', 'created_at': '2026-10-12',
    }])
    source_run_store.save_source_run(day, {'hn': 'unavailable', 'reddit': {'r/ClaudeAI': 'unavailable'}})
    assert day in storage.get_all_dates()
    response = TestClient(app).get(f'/api/briefing/{day}')
    assert response.status_code == 200
    assert response.json()['items'] == []
    assert response.json()['signals']['events'] == []
    assert response.json()['signals']['source_status']['hn'] == 'unavailable'


def test_collect_only_day_reports_selection_pending_not_unavailable(isolated_daily_files, monkeypatch):
    day = '2026-10-13'
    storage.store_content_items([{
        'id': 'hn-1', 'source': 'Hacker News', 'source_type': 'hn',
        'title': 'Native hot story', 'url': 'https://news.ycombinator.com/item?id=1',
        'summary': 'A detailed launch with verifiable source material.', 'created_at': day,
    }])
    source_run_store.save_source_run(day, {'hn': 'ok', 'reddit': {}})
    monkeypatch.setattr(briefing_generator, 'load_event_radar', lambda date: {})
    response = TestClient(app).get(f'/api/briefing/{day}')
    assert response.status_code == 200
    assert response.json()['signals']['events'] == []
    assert response.json()['signals']['selection_status'] == 'not_run'


@pytest.mark.asyncio
async def test_today_only_runs_event_selection_after_quick_reads(monkeypatch):
    order = []
    async def collect(target_date=None):
        order.append('collect')
    async def radar(date):
        order.append('events')
    monkeypatch.setattr(collector, 'run_collection', collect)
    monkeypatch.setattr(collector, '_run_batch_quick_reads', lambda date: order.append('quick_reads'))
    monkeypatch.setattr(collector, 'run_event_radar', radar, raising=False)
    monkeypatch.setattr(collector, '_load_content_file', lambda date: [])
    today = datetime.now().strftime('%Y-%m-%d')
    await collector.run_daily(today)
    assert order == ['collect', 'quick_reads', 'events']
    order.clear()
    await collector.run_daily('2026-01-01')
    assert order == ['collect', 'quick_reads']
