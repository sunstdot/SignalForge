"""Native HN topstories collection; all requests are handled by MockTransport."""
import httpx
import pytest

from backend.services.hn_top_fetcher import fetch_hn_top


@pytest.mark.asyncio
async def test_top_story_keeps_publication_date_rank_and_discussion_url():
    def respond(request):
        if request.url.path.endswith('/topstories.json'):
            return httpx.Response(200, json=[123, 456])
        if request.url.path.endswith('/123.json'):
            return httpx.Response(200, json={
                'id': 123, 'type': 'story', 'title': 'Show HN: Agent compiler',
                'time': 1791885600, 'url': 'https://example.com/compiler',
                'text': '<p>Working compiler with benchmark data.</p>',
                'score': 42, 'descendants': 8, 'by': 'builder',
            })
        return httpx.Response(200, json={
            'id': 456, 'type': 'story', 'title': 'Too old',
            'time': 1791626400, 'url': 'https://example.com/old',
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await fetch_hn_top(client, '2026-10-13', limit=2)

    assert result['status'] == 'ok'
    assert len(result['items']) == 1
    item = result['items'][0]
    assert item['id'] == 'hn-123'
    assert item['published_at'] == '2026-10-13T10:00:00+00:00'
    assert item['created_at'] == '2026-10-13'
    assert item['original_content'] == 'Working compiler with benchmark data.'
    assert item['metadata']['rank'] == 1
    assert item['metadata']['discussion_url'] == 'https://news.ycombinator.com/item?id=123'
    assert item['metadata']['volume'] == 50


@pytest.mark.asyncio
async def test_top_list_timeout_is_unavailable_not_successfully_empty():
    def timeout(request):
        raise httpx.ReadTimeout('top list timed out', request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        result = await fetch_hn_top(client, '2026-10-13')

    assert result == {'status': 'unavailable', 'items': []}


@pytest.mark.asyncio
async def test_partial_item_failure_does_not_discard_success_and_unknown_date_is_not_invented():
    def respond(request):
        path = request.url.path
        if path.endswith('/topstories.json'):
            return httpx.Response(200, json=[123, 456, 789])
        if path.endswith('/789.json'):
            return httpx.Response(503)
        if path.endswith('/456.json'):
            return httpx.Response(200, json={'id': 456, 'type': 'story', 'title': 'Undated'})
        return httpx.Response(200, json={
            'id': 123, 'type': 'story', 'title': 'A working project',
            'time': 1791885600, 'text': 'Source code and benchmarks.',
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await fetch_hn_top(client, '2026-10-13', limit=3)

    assert result['status'] == 'partial'
    assert [item['id'] for item in result['items']] == ['hn-123']
    assert result['items'][0]['url'] == 'https://news.ycombinator.com/item?id=123'
