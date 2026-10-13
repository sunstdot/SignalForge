"""Anonymous public X HTML is untrusted and never treated as a complete timeline."""
import httpx
import pytest

from backend.services.x_public_profile import parse_public_profile, fetch_public_profile


HANDLE = 'oran_ge'
QUOTE_ID = '2109821043506610569'  # independently checked against visible '6h' on 2026-10-13
ORIGINAL_ID = '2109633997966057938'


def article(author, ident, body, *, nested='', marker=''):
    return (f'<article><a href="/{author}">User @{author}</a>'
            f'<a href="/{author}/status/{ident}">6h</a>'
            f'<div>{marker}</div><div>{body}</div>{nested}</article>')


def test_quotes_and_originals_keep_own_author_time_and_text_not_quoted_authors():
    quoted = article('Vincent_AINotes', '2109533044407439607', 'Unrelated quoted body')
    html = '<main>' + article(HANDLE, QUOTE_ID, 'My own interpretation of a new AI release.', nested=quoted) + (
        article(HANDLE, ORIGINAL_ID, 'Original published analysis and benchmark details.')) + '</main>'
    result = parse_public_profile(html, HANDLE, '2026-10-13')
    assert result['status'] == 'partial'  # first public profile page, never full timeline
    assert [post['metadata']['post_type'] for post in result['posts']] == ['quote', 'original']
    assert [post['id'] for post in result['posts']] == [f'x-account-{QUOTE_ID}', f'x-account-{ORIGINAL_ID}']
    assert result['posts'][0]['published_at'] == '2026-10-13T01:38:30.008000+00:00'
    assert result['posts'][0]['metadata']['quoted_url'] == 'https://x.com/Vincent_AINotes/status/2109533044407439607'
    assert result['posts'][0]['original_content'] == 'My own interpretation of a new AI release.'
    assert all(post['metadata']['account'] == '@oran_ge' for post in result['posts'])
    assert all('Unrelated quoted body' not in post['original_content'] for post in result['posts'])


def test_reply_repost_foreign_author_and_ambiguous_quote_are_excluded():
    reply = article(HANDLE, '2109598153699963149', 'I am replying to an existing thread', marker='Replying to @friend')
    repost = article(HANDLE, '2109435789549715933', 'Someone else said this', marker='User Reposted')
    foreign = article('other', '2109821043506610569', 'Not the followed account')
    ambiguous = article(HANDLE, QUOTE_ID, 'Quote cannot be verified', nested='<article>Unverified embed</article>')
    result = parse_public_profile('<main>' + reply + repost + foreign + ambiguous + '</main>', HANDLE, '2026-10-13')
    assert result['posts'] == []
    assert result['status'] == 'partial'  # observed posts were skipped, not no-posts


def test_login_and_unknown_empty_page_never_claim_no_posts():
    assert parse_public_profile('<html>Log in to X</html>', HANDLE, '2026-10-13')['status'] == 'unavailable'
    assert parse_public_profile('<main></main>', HANDLE, '2026-10-13')['status'] == 'unavailable'
    empty = parse_public_profile('<main>@oran_ge hasn\'t posted</main>', HANDLE, '2026-10-13')
    assert empty['status'] == 'ok' and empty['posts'] == []


@pytest.mark.asyncio
async def test_http_rate_limit_is_unavailable_without_any_fabricated_post():
    def response(request):
        assert request.url.host == 'x.com'
        assert request.url.path == '/oran_ge'
        assert 'Cookie' not in request.headers
        return httpx.Response(429)
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        result = await fetch_public_profile(client, HANDLE, '2026-10-13')
    assert result['status'] == 'unavailable'
    assert result['posts'] == []


@pytest.mark.asyncio
async def test_timeout_and_invalid_handle_fail_closed():
    def timeout(request):
        raise httpx.ReadTimeout('public page did not answer', request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        result = await fetch_public_profile(client, HANDLE, '2026-10-13')
    assert result['status'] == 'unavailable'
    with pytest.raises(ValueError):
        parse_public_profile('<main></main>', '../other', '2026-10-13')
