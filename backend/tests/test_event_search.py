"""Verification must not count the seed as corroboration or hide missing platforms."""
import httpx
import pytest

from backend.services.event_search import verify_event


EVENT = {
    'id': 'event-compiler', 'title': 'Agent Compiler released', 'entity': 'Agent Compiler',
    'query': 'Agent Compiler',
    'sources': [{'id': 'hn-123', 'url': 'https://example.com/agent-compiler',
                 'source': 'Hacker News', 'author': 'builder'}],
}


@pytest.mark.asyncio
async def test_other_hn_story_is_discussion_but_original_seed_is_not(tmp_path):
    called = []
    def respond(request):
        called.append((request.url.host, request.url.path))
        if request.url.host == 'hn.algolia.com':
            return httpx.Response(200, json={'hits': [
                {'objectID': '123', 'title': 'Agent Compiler released',
                 'url': 'https://example.com/agent-compiler', 'author': 'builder',
                 'created_at': '2026-10-13T10:00:00Z'},
                {'objectID': '456', 'title': 'Agent Compiler independent benchmarks',
                 'url': 'https://independent.dev/benchmarks', 'author': 'reviewer',
                 'created_at': '2026-10-13T11:00:00Z', 'points': 12, 'num_comments': 5},
            ]})
        assert request.url.host == 'www.reddit.com'
        return httpx.Response(429)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await verify_event(client, EVENT, '2026-10-13', cache_dir=tmp_path)

    assert result['x'] == {'status': 'unavailable', 'posts': []}
    assert result['reddit']['status'] == 'unavailable'
    assert result['hn']['status'] == 'found'
    assert [p['url'] for p in result['hn']['posts']] == ['https://news.ycombinator.com/item?id=456']
    assert result['hn']['posts'][0]['author'] == 'reviewer'
    assert result['hn']['posts'][0]['published_at'] == '2026-10-13T11:00:00Z'
    assert result['hn']['posts'][0]['engagement'] == {'points': 12, 'comments': 5}
    assert {host for host, _ in called} == {'hn.algolia.com', 'www.reddit.com'}


@pytest.mark.asyncio
async def test_successfully_empty_search_differs_from_unavailable_search(tmp_path):
    def respond(request):
        if request.url.host == 'hn.algolia.com':
            assert request.url.params['query'] == 'Agent Compiler'
            return httpx.Response(200, json={'hits': []})
        return httpx.Response(200, text='<feed xmlns="http://www.w3.org/2005/Atom"></feed>')

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await verify_event(client, EVENT, '2026-10-13', cache_dir=tmp_path)

    assert result['hn'] == {'status': 'no_results', 'posts': []}
    assert result['reddit'] == {'status': 'no_results', 'posts': []}
    assert result['x'] == {'status': 'unavailable', 'posts': []}


@pytest.mark.asyncio
async def test_successful_platform_is_cached_but_rate_limited_platform_can_retry(tmp_path):
    calls = {'hn': 0, 'reddit': 0}
    def respond(request):
        if request.url.host == 'hn.algolia.com':
            calls['hn'] += 1
            return httpx.Response(200, json={'hits': []})
        calls['reddit'] += 1
        return httpx.Response(429)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        await verify_event(client, EVENT, '2026-10-13', cache_dir=tmp_path)
        await verify_event(client, EVENT, '2026-10-13', cache_dir=tmp_path)
    assert calls == {'hn': 1, 'reddit': 2}


@pytest.mark.asyncio
async def test_reddit_login_page_is_unavailable_not_zero_discussion(tmp_path):
    def respond(request):
        if request.url.host == 'hn.algolia.com':
            return httpx.Response(200, json={'hits': []})
        return httpx.Response(200, text='<html>Log in to view Reddit</html>')
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await verify_event(client, EVENT, '2026-10-13', cache_dir=tmp_path)
    assert result['reddit']['status'] == 'unavailable'
