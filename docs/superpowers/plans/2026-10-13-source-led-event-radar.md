# Source-Led Event Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace default broad-topic searches with evidence-backed events discovered from existing sources, HN's native top list, and eleven followed Reddit communities.

**Architecture:** Independently collect bounded HN/Reddit source items, retain every existing feed, use one cached batch LLM decision to select up to five concrete events, then query HN/Reddit and optional anonymous X with per-platform coverage statuses. Add `signals.events` to the existing briefing API and render event cards; the separate [public X accounts plan](2026-10-13-public-x-account-watch.md) adds `signals.accounts` later.

**Tech Stack:** Python 3.12, FastAPI, httpx, BeautifulSoup, ElementTree/defusedxml, pytest; React/Vite, Node test runner, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-13-source-led-discovery-design.md` (read in full before execution). Read-only preflight on 2026-10-13: native HN topstories returned 200; one Reddit RSS request returned a real Atom entry, followed by 429s on rapid requests. Do not treat that one success as reliable Reddit coverage.

## Global Constraints

- Execute inline in `happy-v2` unless the user changes that decision. Preserve `.claude/worktrees/...`, untracked `pnpm-lock.yaml`/`pnpm-workspace.yaml`, existing content files, and unrelated work.
- Preserve all RSS, Anthropic fallback, content history, interactive last30days, legacy `signals.inspiration/execution`, and full `items` response. Turn off only four **default automatic topic jobs**; retain their configuration for opt-in/manual use.
- No new credentials, paid service, X login, or X API call. An inaccessible public channel means `unavailable`, not `no_results`. Never claim full X or Reddit coverage.
- At most **one additional selection-model request per day**. Existing quick-read batching may use more tokens as items are added; bound new item counts. No per-event Wingsbot research.
- No fixed topic keywords for *discovery*; event names and URLs derived from source documents may be used for *verification searches*. Maximum five events, possibly zero.
- Every new network call has timeouts, modest limits, origin attribution, error isolation, and rerun-safe caching. Historical-date runs and API GET do not launch live searches or LLM work.
- TDD for every behavior: run a targeted failing test before production changes. Full backend, frontend, build and one browser regression before completion. Do not run `pnpm daily`/live Wingsbot research as a test.

## File map and interface contract

- `backend/services/hn_top_fetcher.py`: `async fetch_hn_top(client: httpx.AsyncClient, day: str, limit: int = 20) -> dict`, returning `{items: list[content_item], status: "ok"|"partial"|"unavailable"}`.
- `backend/services/subreddit_fetcher.py`: `async fetch_subreddits(client: httpx.AsyncClient, day: str, names: list[str], max_per_sub: int = 3) -> dict`, returning `{items: [...], statuses: {"r/Name": "ok"|"partial"|"unavailable"}}`; rate-limited, no speculative fill.
- `backend/services/source_run_store.py`: atomic `save_source_run(day: str, payload: dict)`, `load_source_run(day: str) -> dict`; isolate status from content.
- `backend/services/event_selector.py`: `select_events(day: str, items: list[dict], quick_reads: dict[str, str], *, cache_dir: Path, ask=chat) -> list[dict]`; selection cache prevents repeat model calls, validates source IDs and stable event IDs.
- `backend/services/event_search.py`: `async verify_event(client: httpx.AsyncClient, event: dict, day: str, *, cache_dir: Path) -> dict`; returns `{"x": {"status": ..., "posts": [...]}, "hn": ..., "reddit": ...}` with statuses `found/no_results/partial/unavailable`. Direct HN/Reddit calls; anonymous X provider optional and unavailable by default if no supported public endpoint.
- `backend/services/event_radar.py`: `async run_event_radar(day: str, ...) -> dict`, stores final per-date events atomically; `load_event_radar(day: str) -> dict` has no IO besides local file reads. Must be callable independently from a controlled test without the collector.
- `backend/services/collector.py`: wire new sources to `fetch_all_sources`, cap additional quick reads, invoke event radar after quick reads on **today only**.
- `backend/services/briefing_generator.py`, `backend/services/storage.py`, `frontend/src/pages/BriefingPage.jsx`: expose cached events/status on API and static snapshot, keep old-date fallback and existing archive.
- Tests beside these modules (`backend/tests/test_hn_top_fetcher.py`, `test_subreddit_fetcher.py`, `test_event_selector.py`, `test_event_search.py`, `test_event_radar.py`, `test_event_briefing.py`), plus `frontend/tests/eventRadar.browser.test.mjs`.

---

### Task 1: Bounded native Hacker News discovery

**Files:** Create `backend/services/hn_top_fetcher.py`, `backend/tests/test_hn_top_fetcher.py`.

**Interfaces:** No earlier tasks. Produces `fetch_hn_top(client, day, limit=20)` in the file-map format. Fetch `https://hacker-news.firebaseio.com/v0/topstories.json`, then bounded `/v0/item/{id}.json` (≤4 concurrent; 8-second requests), preserving actual UTC publication date and HN comments URL. A title-only story can be archived and its URL can be matched to a substantive RSS or blog story, but its title alone must not be passed to the model as proof of the external article's claims.

- [ ] **Step 1: Write an offline failing httpx.MockTransport test for HN normal and timeout paths.**

```python
import httpx, pytest
from backend.services.hn_top_fetcher import fetch_hn_top

@pytest.mark.asyncio
async def test_top_story_keeps_hn_id_date_and_discussion_link():
    def respond(request):
        if request.url.path.endswith('/topstories.json'):
            return httpx.Response(200, json=[123])
        return httpx.Response(200, json={"id": 123, "title": "Show HN: Agent compiler", "time": 1791885600,
                                         "url": "https://example.com/compiler", "text": "A working compiler with benchmarks.",
                                         "score": 42, "descendants": 8, "by": "builder"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await fetch_hn_top(client, '2026-10-13', limit=1)
    assert result['status'] == 'ok'
    assert result['items'][0]['id'] == 'hn-123'
    assert result['items'][0]['published_at'].startswith('2026-10-13')
    assert result['items'][0]['metadata']['discussion_url'] == 'https://news.ycombinator.com/item?id=123'
```

Add a second test where the top-list request raises `httpx.ReadTimeout` and returns `unavailable` with no items, not `ok`/empty. Test the two-day freshness window and a missing `time` without manufacturing a date.

- [ ] **Step 2: Verify RED.** Run `cd backend && source venv/bin/activate && python -m pytest tests/test_hn_top_fetcher.py -q`. Expect import failure because the module does not exist.
- [ ] **Step 3: Implement the minimum adapter.** Use `datetime.fromtimestamp(raw['time'], timezone.utc)` and `date.fromisoformat(day)` to check publication between `day-2` and `day`:

```python
published = datetime.fromtimestamp(story['time'], timezone.utc)
if not date.fromisoformat(day) - timedelta(days=2) <= published.date() <= date.fromisoformat(day):
    continue
item_id = f"hn-{story['id']}"
discussion_url = f"https://news.ycombinator.com/item?id={story['id']}"
```

Build stable `hn-{id}` items with `created_at=day`, `published_at=ISO`, `source_type='hn'`, `source='Hacker News'`, `original_content` from nonempty story text/description (never invent), metadata `{origin:'hn_top', rank, fetched_at, discussion_url, author, volume:score+descendants, engagement:'42 points, 8 comments'}` (only include numeric fields if returned by HN). Use `BeautifulSoup(...).get_text()` to strip story HTML. A failed item should make status `partial` while preserving successful stories.
- [ ] **Step 4: Verify GREEN** with the targeted command; run `python -m pytest tests/test_anthropic_blog_integration.py tests/test_collector_daily.py -q` to check existing source handling.
- [ ] **Step 5: Commit only these two files** with `git add backend/services/hn_top_fetcher.py backend/tests/test_hn_top_fetcher.py && git commit -m "feat: collect native HN top stories"`.

### Task 2: Followed Reddit communities with explicit rate-limit status

**Files:** Create `backend/services/subreddit_fetcher.py`, `backend/tests/test_subreddit_fetcher.py`.

**Interfaces:** No HN dependency. Produces `fetch_subreddits(client, day, names, max_per_sub=3)`. Default public Atom/RSS URL is `https://www.reddit.com/r/{validated_name}/hot/.rss?limit=3`, optionally try `new/.rss` once per community if hot succeeds and budget permits; never scrape a login challenge. A 403/429/time-out is `unavailable`, not a valid empty result. Do not silently rewrite `ArtificialInteligence` to another subreddit.

- [ ] **Step 1: Write failing fixture tests** using `httpx.MockTransport` with a minimal Atom `<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>t3_abc</id><title>New agent workflow</title><link href="https://www.reddit.com/r/AI_Agents/comments/abc/post/"/><published>2026-10-13T10:00:00Z</published><content type="html">Detailed implementation and benchmarks</content></entry></feed>`. Assert `reddit-abc`, `source_type='reddit'`, actual `published_at`, `metadata.subreddit='AI_Agents'`, and no fabricated engagement when the feed provides none:

```python
assert result['items'][0]['id'] == 'reddit-abc'
assert result['items'][0]['published_at'] == '2026-10-13T10:00:00+00:00'
assert result['items'][0]['metadata']['subreddit'] == 'AI_Agents'
assert result['items'][0]['metadata'].get('engagement') is None
```
 A second subreddit returning 429 must be `unavailable` while the first one's items survive, and an unqueried third community must be marked `unavailable` without making a third request. Test a 200 feed with zero entries as `ok`/empty, invalid name rejection, and a stale entry excluded.
- [ ] **Step 2: Verify RED.** `cd backend && source venv/bin/activate && python -m pytest tests/test_subreddit_fetcher.py -q` must fail on missing module.
- [ ] **Step 3: Implement parser and bounded requests.** Validate names with `re.fullmatch(r'[A-Za-z0-9_]{1,32}', name)`. Parse Atom using `defusedxml.ElementTree`, normalize `t3_` ID, HTML-unescape content, keep URL/author/date and created-at day, cap at 3 per subreddit and at most two feed requests per community:

```python
root = defusedxml.ElementTree.fromstring(response.content)
ns = {'atom': 'http://www.w3.org/2005/Atom'}
entries = root.findall('atom:entry', ns)[:max_per_sub]
post_id = (entries[0].findtext('atom:id', default='', namespaces=ns)).removeprefix('t3_')
```
 Space requests by at least 1 second; on first 429, stop further Reddit requests for that run and mark the untouched communities `unavailable` with `rate_limited` reason instead of hammering all eleven; return per-sub statuses. Do not include view counts as engagement; unavailable subs do not halt others.
- [ ] **Step 4: Verify GREEN** with the targeted tests and `python -m pytest tests/test_last30days_importer.py -q` (interactive imports remain intact).
- [ ] **Step 5: Commit** with `git add backend/services/subreddit_fetcher.py backend/tests/test_subreddit_fetcher.py && git commit -m "feat: collect selected Reddit community feeds"`.

### Task 3: Wire source collection and stop automatic broad watchlist topics

**Files:** Create `backend/services/source_run_store.py`, `backend/tests/test_source_collection.py`; modify `backend/services/collector.py`, `backend/config/collector.yaml`, `backend/tests/test_collector_daily.py`.

**Interfaces:** Consumes Task 1/2 adapters; `load_source_run(day)` supplies coverage later. Source fetches are asynchronous and included in `fetch_all_sources`; storage of source health is separate and atomic. Keep `sources.watchlist.topics` exactly as-is but set `enabled: false`. Add config `sources.hn_top: {enabled: true, limit: 20}` and `sources.reddit_communities: {enabled: true, max_per_sub: 3, names: [AI_Agents, aipromptprogramming, Anthropic, artificial, ArtificialInteligence, AskReddit, BeAmazed, ChatGPT, ChatGPTCoding, ClaudeAI, DeepSeek]}`.

- [ ] **Step 1: Write failing integration tests** for `fetch_all_sources` with mocked Task 1/2 functions returning one HN, one Reddit item, and one 429 status; assert both items retained, coverage recorded per source, existing RSS still fetched, default config leaves original broad topics but disables daily watchlist. Add a `run_collection('2026-10-12')` test asserting no *live* HN/Reddit/X is triggered on historical backfill. Add a `_run_batch_quick_reads` test: 30 fresh `metadata.origin='reddit_subreddit'` items → at most 20 new social items enter the quick-read batch, existing RSS items still eligible. The config assertion must compare existing topic values exactly:

```python
assert config['sources']['watchlist']['enabled'] is False
assert config['sources']['watchlist']['topics'] == ['AI agent', 'vibe coding', 'RAG', 'LLM new model']
assert len(config['sources']['reddit_communities']['names']) == 11
```
 Mock `collector.chat` at the network boundary, not `store_content_items` if the test asserts storage behavior.
- [ ] **Step 2: Verify RED.** `cd backend && source venv/bin/activate && python -m pytest tests/test_source_collection.py tests/test_collector_daily.py -q` fails on missing integration.
- [ ] **Step 3: Implement integration.** Open a single `httpx.AsyncClient(timeout=8, follow_redirects=True)` per daily source phase; call source adapters with explicit limits and isolate exceptions:

```python
async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
    hn = await fetch_hn_top(client, target_date, limit=20)
    reddit = await fetch_subreddits(client, target_date, reddit_names, max_per_sub=3)
all_items.extend(hn['items'])
all_items.extend(reddit['items'])
save_source_run(target_date, {'hn': hn['status'], 'reddit': reddit['statuses']})
```
 Persist source statuses to `data/source_runs/{day}.json` by temp-file replacement. Only current-day runs make live source requests; test dates never require a network connection. Ensure existing RSS and company-blog tasks still run and HN Daily RSS is not removed. Apply new-source quick-read caps before `chat()` is invoked, without capping original sources. `watchlist.enabled: false` must not remove the `watchlist.topics` or accounts keys.
- [ ] **Step 4: Verify GREEN** using the targeted command plus `python -m pytest tests/test_signal_feed.py tests/test_watchlist_daily.py -q`.
- [ ] **Step 5: Commit** precisely the five files above with message `feat: integrate bounded HN Reddit discovery`.

### Task 4: Once-per-day evidence-based event selection

**Files:** Create `backend/services/event_selector.py`, `backend/tests/test_event_selector.py`.

**Interfaces:** `select_events(day, items, quick_reads, cache_dir=EVENT_DIR, ask=chat) -> list[dict]`. Output each event as `{id, title, what_happened, why_read, seed_ids, entity, query}`; `query` contains a *specific* project/product/event name from the seed, not generic watchlist words. A selection file `{day}.selection.json` caches successful selection even if `events=[]`, keyed by date and prompt version. Only source IDs from input are accepted; canonical ID is stable across reruns for a given set of normalized seed URLs/entity.

- [ ] **Step 1: Write failing tests** with two stories covering the same product (`hn-123`, `reddit-abc`) and one unrelated AskReddit post. `ask` returns JSON `{"events":[{"title":"Agent Compiler","what_happened":"A new compiler has reproducible benchmarks.","why_read":"The method could improve agent workflows.","seed_ids":["hn-123","reddit-abc"],"entity":"Agent Compiler","query":"Agent Compiler"}]}`. Assert one event with two seed IDs, citations from real seed URLs, no irrelevant post, and `ask` invoked exactly once across two calls for the same date/cache. A second test returns unknown seed ID and expects zero events (not a fabricated link); another submits title-only sources and checks `ask` is not called. A cross-day test runs the same canonical source/entity on consecutive dates and expects no duplicate event; if a new verifiable seed describes a new change, it retains the stable ID with `progress: true`. Use `tmp_path` for cache:

```python
calls = []
def fake_ask(messages):
    calls.append(messages)
    return '{"events":[{"title":"Agent Compiler","what_happened":"Published benchmarks.","why_read":"Reproducible build.","seed_ids":["hn-123","reddit-abc"],"entity":"Agent Compiler","query":"Agent Compiler"}]}'
first = select_events('2026-10-13', items, reads, cache_dir=tmp_path, ask=fake_ask)
second = select_events('2026-10-13', items, reads, cache_dir=tmp_path, ask=fake_ask)
assert first == second
assert len(first) == 1
assert len(calls) == 1
```

- [ ] **Step 2: Verify RED** with `cd backend && source venv/bin/activate && python -m pytest tests/test_event_selector.py -q`.
- [ ] **Step 3: Implement bounded selection and validation.** Deduplicate input by canonical URL, require substantive `original_content`/summary and source date, cap the prompt to 60 candidates across blogs/RSS, projects/papers, HN, Reddit, and saved account posts (max 20 per group, redistribute unused slots); each excerpt has at most 400 characters. Include AI-related broad-community posts via the batch decision, not fixed discovery keywords. Pass titles, excerpts, IDs and URLs as **untrusted data** to `chat([{'role':'user','content':prompt}])` once. Parse exactly one JSON object; reject invented IDs/URLs, non-specific generic query, repeated entity, or non-substantive reason, cap five, link sources using original input. Compare the stable normalized entity/seed URL against yesterday's saved selection, omitting an unchanged event and marking a changed, evidenced event `progress: true`. A failed model call records a failure state and makes no second automatic model call that day; a later explicit retry requires authorization or waits until the next day. A minimal validation boundary is:

```python
allowed = {item['id']: item for item in candidates}
valid = [draft for draft in payload['events'][:5]
         if draft['seed_ids'] and all(seed in allowed for seed in draft['seed_ids'])]
```
 Never invent events. Cache successful empty selections to prevent duplicate fees.
- [ ] **Step 4: Verify GREEN** with targeted tests plus `python -m pytest tests/test_signal_feed.py -q`.
- [ ] **Step 5: Commit** `backend/services/event_selector.py backend/tests/test_event_selector.py` with `feat: select a bounded set of source-backed events`.

### Task 5: Verify event discussion without another model run

**Files:** Create `backend/services/event_search.py`, `backend/services/event_radar.py`, `backend/tests/test_event_search.py`, `backend/tests/test_event_radar.py`.

**Interfaces:** Consumes `select_events()` and `load_source_run()`. `verify_event(client, event, day, cache_dir=EVENT_DIR)` returns exactly `x/hn/reddit` keys, each with `{status, posts}`, using allowed statuses `found/no_results/partial/unavailable`. `run_event_radar(day, ...)` composes cached selection plus searches and saves final `data/event_radar/{day}.json` atomically. Use injected `client`/selectors and `tmp_path` to test without external calls.

- [ ] **Step 1: Write failing tests** where an Algolia `200` result with a different HN ID produces `found`, the original HN seed result never counts as independent corroboration, and a Reddit `429` produces `unavailable`, not `no_results`. X anonymous search with no confirmed usable provider returns `unavailable` without trying a paid/keyed endpoint. An empty successful HN response returns `no_results`:

```python
assert result['hn']['status'] == 'no_results'
assert result['hn']['posts'] == []
assert result['reddit']['status'] == 'unavailable'
```

Call `run_event_radar()` twice with a cache and assert selector and successful HN query are each invoked once; a failed Reddit query can be retried separately.
- [ ] **Step 2: Verify RED** via `cd backend && source venv/bin/activate && python -m pytest tests/test_event_search.py tests/test_event_radar.py -q`.
- [ ] **Step 3: Implement three independent result adapters and orchestrator.** HN: bounded Algolia search, requiring an exact entity/URL match, preserve original HN post link. Reddit: public search RSS/JSON with strict 8-second timeout, 429/403 marked unavailable; no login/captcha bypass. X: publicly accessible, no-auth provider only if read-only preflight establishes verifiable statuses and post URLs; otherwise immediate `unavailable` with no network/LLM. Reject the seed's original URL, same author restatement and shared copied links as independent proof. Max two query variations per platform and at most 5 returned posts; stable key `(day,event_id,platform,query)` avoids repeating successful searches:

```python
if provider is None:  # no compliant anonymous X search verified
    return {'status': 'unavailable', 'posts': []}
posts = [hit for hit in hits if hit['url'] not in seed_urls][:5]
return {'status': 'found' if posts else 'no_results', 'posts': posts}
```
 Cache each platform status separately, then write final event bundle atomically so partial failures do not erase successes.
- [ ] **Step 4: Verify GREEN** targeted plus `python -m pytest tests/test_last30days_brief.py -q` (existing manual-search behavior unchanged).
- [ ] **Step 5: Commit** the four task files with `feat: attach independently sourced event discussions`.

### Task 6: Briefing contract, UI and existing static snapshots

**Files:** Modify `backend/services/collector.py`, `backend/services/briefing_generator.py`, `backend/services/storage.py`, `frontend/src/pages/BriefingPage.jsx`, `frontend/src/pages/dailySignalData.js`, `README.md`; create `backend/tests/test_event_briefing.py`, `frontend/tests/eventRadar.browser.test.mjs`.

**Interfaces:** Consumes Task 5 `run_event_radar()` and `load_event_radar()`. Extend `/api/briefing/{day}`'s current `signals` object with `events` and `source_status`, retaining `inspiration`, `execution`, `total`, `items`. Event-only dates with a failed source run must still surface a dated status; `GET` never invokes `run_event_radar()`. New UI defaults to Event Tracking when `signals.events` exists; old briefings without the key use the existing dual-track view; keep All Content and historical static snapshots.

- [ ] **Step 1: Write failing tests.** Backend: monkeypatch `load_event_radar(day)` to return one event with primary source URL and `x:unavailable, hn:found, reddit:no_results`; assert `get_briefing_by_date(day)['signals']['events'][0]['discussions']` retains distinct states while `items` and legacy tracks remain. Call GET twice (FastAPI `TestClient`) with cached state and assert network/search/model fakes are untouched. Test a date with no content but a saved failed source run still appears as explicit unavailable date, rather than 404:

```python
from fastapi.testclient import TestClient
from backend.main import app
response = TestClient(app).get('/api/briefing/2026-10-13')
assert response.status_code == 200
assert response.json()['signals']['events'] == []
assert response.json()['signals']['source_status']['hn'] == 'unavailable'
```
 Frontend Playwright: mock same response, verify event title/summary/original link, platform coverage, All Content and fallback on a mock legacy briefing; no extra API call on tab switch.
- [ ] **Step 2: Verify RED.** `cd backend && source venv/bin/activate && python -m pytest tests/test_event_briefing.py -q`; then start Vite on an unused explicit port and run `SIGNAL_FEED_TEST_URL=http://127.0.0.1:5175 node --test tests/eventRadar.browser.test.mjs` from `frontend` after starting Vite with `npm run dev -- --host 127.0.0.1 --port 5175` (check that port 5175 is free; shut Vite down afterwards). Both should fail on missing event UI/contract.
- [ ] **Step 3: Implement integration.** Add `await run_event_radar(day)` **after** `_run_batch_quick_reads(day)` in `run_daily()` only for the actual current day. Briefing generator locally reads cached event and source status; never recomputes selection/search inside GET:

```python
cached = load_event_radar(date)
if cached is not None:
    briefing['signals']['events'] = cached.get('events', [])
    briefing['signals']['source_status'] = load_source_run(date)
```
 Extend `get_all_dates()` to include a date with a saved source-run failure, without classifying unrelated interactive last30days imports as daily. For a status-only failure day, do not silently pass yesterday's fallback items off as today's discoveries: render the outage and label any archival items as prior-day context. Add `getEventItems(briefing)` pure fallback helper and render Event Tracking cards as the new default when available; X `unavailable` is not “0 comments.” Keep existing legacy tracks for older dates and static API snapshots through existing `snapshot_static.py` flow. Document new config/rate and no-auth limitations in README.
- [ ] **Step 4: Verify GREEN** via targeted backend/browser tests; run full `cd backend && source venv/bin/activate && python -m pytest tests/ -q`, `cd frontend && node --test src/**/*.test.mjs src/*.test.mjs`, `npm run build`, browser test, and `git diff --check`. Live HN/Reddit read-only smoke checks are optional; do **not** run `pnpm daily` to test (cost/data writes). Report source availability separately from deterministic test results.
- [ ] **Step 5: Commit** only this task's paths with `git commit -m "feat: show cached cross-platform event radar"`. Confirm `git status --short` still includes only the pre-existing worktree and pnpm artifacts, not staged user changes.
