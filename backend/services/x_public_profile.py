"""Conservative parser for publicly rendered X profiles; no login or private API."""
import re
from datetime import date, datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup


HANDLE = re.compile(r'[A-Za-z0-9_]{1,15}\Z')
STATUS_LINK = re.compile(r'^/([A-Za-z0-9_]{1,15})/status/(\d{15,20})(?:[/?].*)?$', re.I)
SNOWFLAKE_EPOCH_MS = 1288834974657


def _unavailable(reason: str) -> dict:
    return {'posts': [], 'status': 'unavailable',
            'checked_at': datetime.now(timezone.utc).isoformat(), 'reason': reason}


def parse_public_profile(html: str, handle: str, day: str) -> dict:
    """Extract only demonstrably owned originals/quotes from the first public page.

    The first page is never interpreted as a complete account timeline.
    """
    handle = handle.lstrip('@')
    if not HANDLE.fullmatch(handle):
        raise ValueError('invalid X handle')
    today = date.fromisoformat(day)
    soup = BeautifulSoup(html, 'html.parser')
    outer_articles = [article for article in soup.select('article')
                      if article.find_parent('article') is None]
    checked_at = datetime.now(timezone.utc).isoformat()
    if not outer_articles:
        plain = soup.get_text(' ', strip=True)
        explicit_empty = (f'@{handle}'.casefold() in plain.casefold() and
                          bool(re.search(r"hasn't posted|has not posted|尚未发布", plain, re.I)))
        return {'posts': [], 'status': 'ok' if explicit_empty else 'unavailable',
                'checked_at': checked_at,
                'reason': 'confirmed_empty' if explicit_empty else 'no_verifiable_profile_posts'}

    posts = []
    observed = 0
    ambiguous = False
    for outer in outer_articles:
        # A quoted third-party article is *not* a post by the followed handle.
        direct_links = [link for link in outer.select('a[href]')
                        if link.find_parent('article') is outer]
        own_links = [link for link in direct_links
                     if (match := STATUS_LINK.match(link.get('href', '')))
                     and match.group(1).casefold() == handle.casefold()]
        if not own_links:
            continue
        observed += 1
        author_links = [link for link in direct_links
                        if link.get('href', '').rstrip('/').casefold() == f'/{handle}'.casefold()]
        if not any(f'@{handle}'.casefold() in link.get_text(' ', strip=True).casefold()
                   for link in author_links):
            ambiguous = True
            continue
        owned = own_links[0]
        match = STATUS_LINK.match(owned.get('href', ''))
        status_id = match.group(2)
        try:
            published = datetime.fromtimestamp(
                ((int(status_id) >> 22) + SNOWFLAKE_EPOCH_MS) / 1000, timezone.utc)
        except (ValueError, OverflowError, OSError):
            ambiguous = True
            continue
        if not today - timedelta(days=2) <= published.date() <= today:
            continue  # old post is not an unknown/failed post
        clone = BeautifulSoup(str(outer), 'html.parser').select_one('article')
        for nested in clone.select('article'):
            nested.decompose()
        own_text = clone.get_text(' ', strip=True)
        if re.search(r'\bReplying to\b|正在回复|回复\s*@', own_text, re.I):
            continue
        if re.search(r'\bReposted\b|\bRetweeted\b|转发了|转推了', own_text, re.I):
            continue
        quoted = outer.select('article')
        quoted_url = ''
        if quoted:
            if len(quoted) != 1:
                ambiguous = True
                continue
            links = [link for link in quoted[0].select('a[href]')
                     if link.find_parent('article') is quoted[0]
                     and STATUS_LINK.match(link.get('href', ''))]
            if not links:
                ambiguous = True
                continue
            quoted_url = 'https://x.com' + links[0]['href'].split('?', 1)[0]
        marker = owned.get_text(' ', strip=True)
        own_body = own_text.split(marker, 1)[-1].strip() if marker and marker in own_text else ''
        if not own_body:
            ambiguous = True
            continue
        metadata = {
            'origin': 'x_public_account', 'account': f'@{handle}', 'author': f'@{handle}',
            'post_type': 'quote' if quoted_url else 'original',
            'source_published_at': published.isoformat(),
        }
        if quoted_url:
            metadata['quoted_url'] = quoted_url
        posts.append({
            'id': f'x-account-{status_id}', 'source': f'X:@{handle}', 'source_type': 'x',
            'title': own_body[:100], 'url': f'https://x.com/{handle}/status/{status_id}',
            'summary': own_body[:500], 'original_content': own_body[:4000],
            'published_at': published.isoformat(), 'created_at': day,
            'relevance_score': 8, 'metadata': metadata,
        })
    if not observed:
        return _unavailable('no_owned_status_links')
    return {'posts': posts, 'status': 'partial', 'checked_at': checked_at,
            'reason': 'ambiguous_posts_or_first_page_only' if ambiguous else 'public_profile_first_page_only'}


async def fetch_public_profile(client: httpx.AsyncClient, handle: str, day: str) -> dict:
    """Fetch one anonymous public page. No credentialed or anti-bot fallback."""
    clean_handle = handle.lstrip('@')
    if not HANDLE.fullmatch(clean_handle):
        raise ValueError('invalid X handle')
    if len(client.cookies):
        return _unavailable('authenticated_client_not_allowed')
    try:
        response = await client.get(f'https://x.com/{clean_handle}',
                                    headers={'User-Agent': 'SignalForge/0.1 (public profile only)'},
                                    timeout=8)
        response.raise_for_status()
        if response.url.host != 'x.com' or not response.headers.get('content-type', '').startswith('text/html'):
            return _unavailable('unexpected_public_response')
        return parse_public_profile(response.text, clean_handle, day)
    except httpx.HTTPStatusError as exc:
        return _unavailable(f'http_{exc.response.status_code}')
    except (httpx.HTTPError, ValueError):
        return _unavailable('public_profile_unreachable')
