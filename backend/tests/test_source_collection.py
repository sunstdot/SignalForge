"""Source-led discovery integrates without replacing any existing source."""
from datetime import datetime
from unittest.mock import patch

import pytest

from backend.services import collector
from backend.services.source_run_store import load_source_run
import backend.services.source_run_store as source_run_store


@pytest.mark.asyncio
async def test_today_collects_hn_reddit_and_rss_and_saves_partial_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr(source_run_store, 'SOURCE_RUN_DIR', tmp_path)
    today = datetime.now().strftime('%Y-%m-%d')
    rss = {'id': 'rss-1', 'title': 'Official release', 'source_type': 'rss',
           'source': 'Official', 'url': 'https://example.com/rss', 'relevance_score': 8}
    hn = {'id': 'hn-123', 'title': 'HN launch', 'source_type': 'hn',
          'source': 'Hacker News', 'url': 'https://example.com/hn', 'relevance_score': 8}
    reddit = {'id': 'reddit-abc', 'title': 'Reddit post', 'source_type': 'reddit',
              'source': 'r/AI_Agents', 'url': 'https://reddit.com/post', 'relevance_score': 8}
    async def rss_fetch(config, target_date=None):
        return [rss]
    async def blog_fetch(target_date=None):
        return []
    async def hn_fetch(client, day, limit=20):
        assert day == today
        return {'status': 'ok', 'items': [hn]}
    async def reddit_fetch(client, day, names, max_per_sub=3):
        assert 'AskReddit' in names
        return {'statuses': {'r/AI_Agents': 'ok', 'r/ClaudeAI': 'unavailable'},
                'errors': {'r/ClaudeAI': 'rate_limited'}, 'items': [reddit]}
    config = {'sources': {
        'rss': {'enabled': True, 'subscriptions': []},
        'hn_top': {'enabled': True, 'limit': 20},
        'reddit_communities': {'enabled': True, 'names': ['AI_Agents', 'AskReddit'], 'max_per_sub': 3},
    }}
    with (patch.object(collector, 'fetch_rss_feeds', side_effect=rss_fetch),
          patch.object(collector, 'fetch_anthropic_technical_articles', side_effect=blog_fetch),
          patch.object(collector, 'fetch_hn_top', side_effect=hn_fetch),
          patch.object(collector, 'fetch_subreddits', side_effect=reddit_fetch)):
        items = await collector.fetch_all_sources(config, target_date=today)

    assert {item['id'] for item in items} == {'rss-1', 'hn-123', 'reddit-abc'}
    assert load_source_run(today)['hn'] == 'ok'
    assert load_source_run(today)['reddit']['r/ClaudeAI'] == 'unavailable'
    assert load_source_run(today)['errors']['r/ClaudeAI'] == 'rate_limited'


@pytest.mark.asyncio
async def test_historical_backfill_does_not_call_live_discovery_adapters(tmp_path, monkeypatch):
    monkeypatch.setattr(source_run_store, 'SOURCE_RUN_DIR', tmp_path)
    async def blog_fetch(target_date=None):
        return []
    with (patch.object(collector, 'fetch_anthropic_technical_articles', side_effect=blog_fetch),
          patch.object(collector, 'fetch_hn_top', side_effect=AssertionError('live HN request')),
          patch.object(collector, 'fetch_subreddits', side_effect=AssertionError('live Reddit request'))):
        result = await collector.fetch_all_sources({'sources': {
            'hn_top': {'enabled': True},
            'reddit_communities': {'enabled': True, 'names': ['AI_Agents']},
        }}, target_date='2026-01-01')
    assert result == []
    assert load_source_run('2026-01-01') == {}


@pytest.mark.asyncio
async def test_disabled_native_hn_is_not_misreported_as_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(source_run_store, 'SOURCE_RUN_DIR', tmp_path)
    today = datetime.now().strftime('%Y-%m-%d')
    async def blog_fetch(target_date=None):
        return []
    async def reddit_fetch(client, day, names, max_per_sub=3):
        return {'statuses': {'r/ClaudeAI': 'ok'}, 'errors': {}, 'items': []}
    with (patch.object(collector, 'fetch_anthropic_technical_articles', side_effect=blog_fetch),
          patch.object(collector, 'fetch_subreddits', side_effect=reddit_fetch)):
        await collector.fetch_all_sources({'sources': {
            'hn_top': {'enabled': False},
            'reddit_communities': {'enabled': True, 'names': ['ClaudeAI']},
        }}, target_date=today)
    coverage = load_source_run(today)
    assert 'hn' not in coverage
    assert coverage['reddit']['r/ClaudeAI'] == 'ok'


def test_default_config_keeps_manual_watchlist_topics_but_disables_auto_search():
    sources = collector.load_config()['sources']
    assert sources['watchlist']['enabled'] is False
    assert sources['watchlist']['topics'] == ['AI agent', 'vibe coding', 'RAG', 'LLM new model']
    assert sources['hn_top']['enabled'] is True
    assert sources['reddit_communities']['names'] == [
        'AI_Agents', 'aipromptprogramming', 'Anthropic', 'artificial',
        'ArtificialInteligence', 'AskReddit', 'BeAmazed', 'ChatGPT',
        'ChatGPTCoding', 'ClaudeAI', 'DeepSeek',
    ]


def test_new_social_items_have_a_quick_read_cap_without_excluding_old_rss(monkeypatch):
    day = '2026-10-13'
    new_items = [
        {'id': f'reddit-{n}', 'title': f'Post {n}', 'summary': 'An actual detailed post',
         'metadata': {'origin': 'reddit_subreddit'}}
        for n in range(30)
    ]
    original = {'id': 'rss-1', 'title': 'Official release', 'summary': 'A full source report'}
    monkeypatch.setattr(collector, '_load_content_file', lambda date: new_items + [original])
    prompts = []
    def fake_chat(messages):
        prompts.append(messages[0]['content'])
        return '[]'
    with (patch.object(collector, 'chat', side_effect=fake_chat),
          patch('backend.services.storage.load_quick_reads', return_value={}),
          patch('backend.services.storage.save_quick_read')):
        collector._run_batch_quick_reads(day)
    assert len(prompts) == 2
    assert sum(prompt.count('标题：') for prompt in prompts) == 21
    assert any('Official release' in prompt for prompt in prompts)
