"""Community feeds are public and best-effort; no real Reddit traffic in tests."""
import httpx
import pytest

from backend.services.subreddit_fetcher import fetch_subreddits


ENTRY = '''<entry><id>t3_abc</id><title>New agent workflow</title>
<link href="https://www.reddit.com/r/AI_Agents/comments/abc/post/"/>
<author><name>builder</name></author><published>2026-10-13T10:00:00Z</published>
<content type="html">&lt;p&gt;Detailed implementation and benchmarks&lt;/p&gt;</content></entry>'''


def feed(entries):
    return f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'


@pytest.mark.asyncio
async def test_real_atom_entry_preserves_date_author_and_link_without_invented_engagement():
    def respond(request):
        assert request.url.path == '/r/AI_Agents/hot/.rss'
        return httpx.Response(200, text=feed(ENTRY))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await fetch_subreddits(client, '2026-10-13', ['AI_Agents'], pause_seconds=0)

    assert result['statuses'] == {'r/AI_Agents': 'ok'}
    assert [item['id'] for item in result['items']] == ['reddit-abc']
    item = result['items'][0]
    assert item['source_type'] == 'reddit'
    assert item['url'] == 'https://www.reddit.com/r/AI_Agents/comments/abc/post/'
    assert item['published_at'] == '2026-10-13T10:00:00+00:00'
    assert item['created_at'] == '2026-10-13'
    assert item['original_content'] == 'Detailed implementation and benchmarks'
    assert item['metadata']['subreddit'] == 'AI_Agents'
    assert item['metadata']['author'] == 'builder'
    assert 'engagement' not in item['metadata']


@pytest.mark.asyncio
async def test_rate_limit_stops_following_communities_without_erasing_previous_posts():
    requested = []

    def respond(request):
        requested.append(request.url.path)
        if request.url.path.startswith('/r/AI_Agents/'):
            return httpx.Response(200, text=feed(ENTRY))
        return httpx.Response(429)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await fetch_subreddits(client, '2026-10-13',
                                        ['AI_Agents', 'ClaudeAI', 'DeepSeek'], pause_seconds=0)

    assert [item['id'] for item in result['items']] == ['reddit-abc']
    assert result['statuses'] == {
        'r/AI_Agents': 'ok', 'r/ClaudeAI': 'unavailable', 'r/DeepSeek': 'unavailable',
    }
    assert result['errors']['r/DeepSeek'] == 'rate_limited'
    assert len(requested) == 2


@pytest.mark.asyncio
async def test_empty_feed_is_covered_but_login_page_is_unavailable():
    def respond(request):
        if '/r/AI_Agents/' in request.url.path:
            return httpx.Response(200, text=feed(''))
        return httpx.Response(200, text='<html>Log in to view Reddit</html>')

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await fetch_subreddits(client, '2026-10-13',
                                        ['AI_Agents', 'Anthropic'], pause_seconds=0)

    assert result['items'] == []
    assert result['statuses'] == {'r/AI_Agents': 'ok', 'r/Anthropic': 'unavailable'}


@pytest.mark.asyncio
async def test_bad_subreddit_name_and_old_or_missing_dates_do_not_fabricate_items():
    old = ENTRY.replace('2026-10-13T10:00:00Z', '2026-10-10T10:00:00Z')
    undated = ENTRY.replace('t3_abc', 't3_xyz').replace('<published>2026-10-13T10:00:00Z</published>', '')
    calls = []

    def respond(request):
        calls.append(request.url.path)
        return httpx.Response(200, text=feed(old + undated))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await fetch_subreddits(client, '2026-10-13',
                                        ['../../private', 'AI_Agents'], pause_seconds=0)

    assert calls == ['/r/AI_Agents/hot/.rss']
    assert result['items'] == []
    assert result['statuses']['r/../../private'] == 'unavailable'
    assert result['statuses']['r/AI_Agents'] == 'partial'
