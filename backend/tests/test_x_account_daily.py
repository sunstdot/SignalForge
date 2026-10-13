"""Followed public profiles are an independent, idempotent daily path."""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from backend.services import collector, storage
import backend.services.x_account_daily as account_daily


DAY = '2026-10-13'


def post(post_id, handle):
    return {
        'id': f'x-account-{post_id}', 'title': f'{handle} original announcement',
        'summary': 'Concrete implementation report.', 'original_content': 'Concrete implementation report.',
        'source_type': 'x', 'source': f'X:@{handle}',
        'url': f'https://x.com/{handle}/status/{post_id}',
        'published_at': f'{DAY}T10:00:00+00:00', 'created_at': DAY,
        'metadata': {'origin': 'x_public_account', 'account': f'@{handle}',
                     'post_type': 'original', 'author': f'@{handle}'},
    }


@pytest.fixture
def account_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'CONTENT_DIR', tmp_path / 'content')
    (tmp_path / 'content').mkdir()
    monkeypatch.setattr(account_daily, 'ACCOUNT_RUN_DIR', tmp_path / 'account_runs')
    return tmp_path


@pytest.mark.asyncio
async def test_four_accounts_keep_independent_coverage_and_rerun_only_failed_one(account_storage, monkeypatch):
    calls = []
    outputs = {
        'oran_ge': {'status': 'partial', 'posts': [post('2109821043506610569', 'oran_ge')]},
        'dotey': {'status': 'partial', 'posts': [post('2109633997966057938', 'dotey')]},
        'fkysly': {'status': 'unavailable', 'posts': [], 'reason': 'http_429'},
        'thsottiaux': {'status': 'ok', 'posts': [], 'reason': 'confirmed_empty'},
    }
    async def fetch(client, handle, day):
        calls.append(handle)
        return {'checked_at': f'{day}T10:00:00+00:00', 'reason': 'first_page_only', **outputs[handle]}
    monkeypatch.setattr(account_daily, 'fetch_public_profile', fetch)
    handles = ['oran_ge', 'dotey', 'fkysly', 'thsottiaux', '@oran_ge']
    first = await account_daily.run_x_account_daily(DAY, handles, today=DAY)
    assert list(first['accounts']) == ['@oran_ge', '@dotey', '@fkysly', '@thsottiaux']
    assert first['accounts']['@fkysly']['status'] == 'unavailable'
    assert first['accounts']['@thsottiaux']['status'] == 'ok'
    assert len(storage._load_content_file(DAY)) == 2
    assert len(list((account_storage / 'account_runs').glob('*.tmp'))) == 0

    second = await account_daily.run_x_account_daily(DAY, handles, today=DAY)
    assert calls.count('oran_ge') == 1 and calls.count('dotey') == 1
    assert calls.count('fkysly') == 2 and calls.count('thsottiaux') == 1
    assert len(storage._load_content_file(DAY)) == 2
    assert account_daily.load_x_account_day(DAY) == second


@pytest.mark.asyncio
async def test_previous_day_and_last30days_post_url_are_not_reinserted(account_storage, monkeypatch):
    old_id = '2109821043506610569'
    fresh_id = '2109878000000000000'
    yesterday = (date.fromisoformat(DAY) - timedelta(days=1)).isoformat()
    prior = {**post(old_id, 'oran_ge'), 'created_at': yesterday}
    storage.store_content_items([prior])
    from_other_source = {**post(fresh_id, 'oran_ge'), 'id': 'x-last30days-1',
                         'url': f'https://twitter.com/oran_ge/status/{fresh_id}?utm_source=search',
                         'metadata': {'origin': 'last30days'}}
    storage.store_content_items([from_other_source])
    new = post('2109879000000000000', 'oran_ge')
    async def fetch(client, handle, day):
        return {'checked_at': f'{day}T10:00:00+00:00', 'status': 'partial', 'reason': 'first_page_only',
                'posts': [post(old_id, 'oran_ge'), post(fresh_id, 'oran_ge'), new]}
    monkeypatch.setattr(account_daily, 'fetch_public_profile', fetch)
    saved = await account_daily.run_x_account_daily(DAY, ['oran_ge'], today=DAY)
    assert len(saved['accounts']['@oran_ge']['posts']) == 3  # verified raw posts survive the display cache
    assert [item['id'] for item in storage._load_content_file(DAY)] == ['x-last30days-1', new['id']]


@pytest.mark.asyncio
async def test_historical_account_run_is_local_read_only(account_storage, monkeypatch):
    async def no_network(client, handle, day):
        raise AssertionError('historical run must not fetch X')
    monkeypatch.setattr(account_daily, 'fetch_public_profile', no_network)
    assert await account_daily.run_x_account_daily('2026-01-01', ['oran_ge'], today=DAY) == {}
    assert not (account_storage / 'account_runs').exists()


def test_quick_reads_reserve_room_for_followed_accounts(monkeypatch):
    day = DAY
    hn = [{'id': f'hn-{i}', 'title': f'Hot story {i}', 'summary': 'Detailed story text',
           'metadata': {'origin': 'hn_top'}} for i in range(30)]
    account = {'id': 'x-account-1', 'title': 'Followed builder', 'summary': 'Detailed post text',
               'metadata': {'origin': 'x_public_account'}}
    monkeypatch.setattr(collector, '_load_content_file', lambda date: hn + [account])
    prompts = []
    def fake_chat(messages):
        prompts.append(messages[0]['content'])
        return '[]'
    with (patch.object(collector, 'chat', side_effect=fake_chat),
          patch('backend.services.storage.load_quick_reads', return_value={}),
          patch('backend.services.storage.save_quick_read')):
        collector._run_batch_quick_reads(day)
    assert sum(prompt.count('标题：') for prompt in prompts) == 20
    assert any('Followed builder' in prompt for prompt in prompts)


def test_default_config_is_editable_and_has_exact_four_followed_handles():
    config = collector.load_config()['sources']['x_public_accounts']
    assert config['enabled'] is True
    assert config['handles'] == ['oran_ge', 'dotey', 'fkysly', 'thsottiaux']


@pytest.mark.asyncio
async def test_collector_calls_accounts_only_for_today_after_original_collection(monkeypatch):
    order = []
    async def regular(config, target_date=None):
        order.append('existing_sources')
        return []
    async def account(day, handles, **kwargs):
        order.append('accounts')
        assert handles == ['oran_ge', 'dotey']
        return {'accounts': {}}
    monkeypatch.setattr(collector, 'fetch_all_sources', regular)
    monkeypatch.setattr(collector, 'run_x_account_daily', account, raising=False)
    monkeypatch.setattr(collector, 'load_config', lambda: {'sources': {
        'x_public_accounts': {'enabled': True, 'handles': ['oran_ge', 'dotey']},
    }})
    monkeypatch.setattr(collector, '_load_content_file', lambda date: [])
    with patch.object(collector, 'store_content_items', return_value=0):
        await collector.run_collection(target_date=date.today().isoformat())
        assert order == ['existing_sources', 'accounts']
        order.clear()
        await collector.run_collection(target_date='2026-01-01')
        assert order == ['existing_sources']
