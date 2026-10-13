"""The account briefing uses only saved public post/cache state."""
from fastapi.testclient import TestClient
import pytest

from main import app
from services import briefing_generator, source_run_store, storage, x_account_daily


@pytest.fixture
def files(tmp_path, monkeypatch):
    for kind in ('content', 'briefings', 'quick_reads', 'account_runs', 'source_runs'):
        (tmp_path / kind).mkdir()
    monkeypatch.setattr(storage, 'CONTENT_DIR', tmp_path / 'content')
    monkeypatch.setattr(storage, 'BRIEFINGS_DIR', tmp_path / 'briefings')
    monkeypatch.setattr(storage, 'QUICK_READS_DIR', tmp_path / 'quick_reads')
    monkeypatch.setattr(storage, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(x_account_daily, 'ACCOUNT_RUN_DIR', tmp_path / 'account_runs')
    monkeypatch.setattr(source_run_store, 'SOURCE_RUN_DIR', tmp_path / 'source_runs')
    return tmp_path


def test_saved_original_and_quote_are_grouped_without_network_or_model(files, monkeypatch):
    day = '2026-10-13'
    original = {
        'id': 'x-account-1', 'source': 'X:@oran_ge', 'source_type': 'x',
        'title': 'Original release', 'url': 'https://x.com/oran_ge/status/2109821043506610569',
        'summary': 'My own original technical description.', 'original_content': 'My own original technical description.',
        'created_at': day, 'published_at': f'{day}T01:38:30+00:00',
        'metadata': {'origin': 'x_public_account', 'account': '@oran_ge', 'post_type': 'original'},
    }
    quote = {
        **original, 'id': 'x-account-2', 'title': 'Quote with new context',
        'url': 'https://x.com/oran_ge/status/2109879000000000000',
        'metadata': {'origin': 'x_public_account', 'account': '@oran_ge', 'post_type': 'quote',
                     'quoted_url': 'https://x.com/other/status/2109533044407439607'},
    }
    storage.store_content_items([original, quote])
    storage.save_quick_read(day, original['id'], '可核验的账号本人原创和技术细节。')
    x_account_daily._save(day, {'date': day, 'accounts': {
        '@oran_ge': {'status': 'partial', 'reason': 'public_profile_first_page_only',
                     'checked_at': f'{day}T12:00:00+00:00', 'posts': [original, quote]},
        '@dotey': {'status': 'unavailable', 'reason': 'http_429',
                   'checked_at': f'{day}T12:00:00+00:00', 'posts': []},
    }}, files / 'account_runs')
    def forbidden(*args, **kwargs):
        raise AssertionError('briefing GET started live X or model calls')
    monkeypatch.setattr(x_account_daily, 'fetch_public_profile', forbidden)
    monkeypatch.setattr(briefing_generator, 'chat', forbidden, raising=False)

    response = TestClient(app).get(f'/api/briefing/{day}')
    assert response.status_code == 200
    payload = response.json()
    assert {i['url'] for i in payload['items']} == {original['url'], quote['url']}
    assert 'inspiration' in payload['signals'] and 'execution' in payload['signals']
    groups = payload['signals']['accounts']
    assert len(groups) == 2
    assert groups[0]['handle'] == '@oran_ge' and groups[0]['status'] == 'partial'
    assert [p['kind'] for p in groups[0]['posts']] == ['original', 'quote']
    assert groups[0]['posts'][0]['takeaway'] == '可核验的账号本人原创和技术细节。'
    assert groups[0]['posts'][1]['quoted_url'] == quote['metadata']['quoted_url']
    assert groups[1]['handle'] == '@dotey' and groups[1]['status'] == 'unavailable'
    assert groups[1]['posts'] == []


def test_account_failure_without_content_is_still_an_explicit_daily_date(files):
    day = '2026-10-13'
    x_account_daily._save(day, {'date': day, 'accounts': {
        '@fkysly': {'status': 'unavailable', 'reason': 'http_429',
                    'checked_at': f'{day}T12:00:00+00:00', 'posts': []},
    }}, files / 'account_runs')
    assert day in storage.get_all_dates()
    response = TestClient(app).get(f'/api/briefing/{day}')
    assert response.status_code == 200
    payload = response.json()
    assert payload['items'] == []
    assert payload['signals']['accounts'][0]['status'] == 'unavailable'
    assert payload['signals']['accounts'][0]['posts'] == []
    assert 'events' not in payload['signals']
