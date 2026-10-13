# Public X Account Watch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Follow four named X accounts by their actual publicly verifiable original/quote posts, with honest per-account coverage and no new login or API authorization.

**Architecture:** First gate the work on a read-only anonymous public-profile probe. Parse verifiable per-post URLs, authors, types and publication times from public profiles, cache bounded daily results and coverage separately from raw content, then expose `signals.accounts` in the existing briefing and add the Account Watch view. This plan stands alone; if the [event radar plan](2026-10-13-source-led-event-radar.md) has run, its Events tab remains the other default section.

**Tech Stack:** Python 3.12, httpx, BeautifulSoup, FastAPI/pytest; React/Vite and Playwright; JSON file storage.

**Spec:** `docs/superpowers/specs/2026-10-13-source-led-discovery-design.md` (read in full before execution).

## Global Constraints

- Work inline in `happy-v2` per user preference; do not stage unrelated `.claude/worktrees/...`, `pnpm-lock.yaml` or `pnpm-workspace.yaml` changes.
- Follow only `@oran_ge`, `@dotey`, `@fkysly`, `@thsottiaux` by actual author, without topic keywords. Keep only original posts and quote posts; exclude ordinary replies and pure reposts. Quote text and original post URL must be distinguishable from quoted third-party content.
- Do not use an X login, cookie, existing X credentials, keyed API, paid provider, anti-bot workaround, or last30days `--x-handle` as a surrogate timeline. If any verifiable field is absent, mark partial/unavailable and skip the dubious post. Never report unavailable as “no posts.”
- A valid post needs actual X status URL, checked author, identifiable type and UTC publication time; cap posts per account, use bounded 8-second requests and independent per-account errors. Persist raw material, including below-threshold posts, separately from UI selection; do not erase earlier content.
- API GET, static snapshots and historical archives must read saved files only. Account fetching is current-day collection, with rerun deduplication across adjacent dates and platform reports. Maintain legacy `signals.inspiration/execution`, old-date fallback, and All Content.
- TDD every task (RED before edits, GREEN after). Mock HTTP and clock in tests; do not run `daily` or make paid searches as a test.

## File map and interface contract

- `backend/services/x_public_profile.py`: `parse_public_profile(html: str, handle: str, day: str) -> dict` and `async fetch_public_profile(client: httpx.AsyncClient, handle: str, day: str) -> dict`; both return `{"posts": [content_item], "status": "ok"|"partial"|"unavailable", "checked_at": ISO_UTC, "reason": str}`. Parser never sends network requests; HTTP adapter hits only `https://x.com/{handle}` anonymously.
- `backend/services/x_account_daily.py`: `async run_x_account_daily(day: str, handles: list[str], *, cache_dir: Path = ACCOUNT_RUN_DIR, client: httpx.AsyncClient | None = None) -> dict` and `load_x_account_day(day: str) -> dict`; per-date JSON cache contains status, checked time, and verified posts by handle; `run` also stores source items via `store_content_items` without copying earlier days.
- `backend/config/collector.yaml`: add `sources.x_public_accounts` with `enabled: true`, four exact handles, `max_posts_per_account: 5`, `lookback_days: 2`. Do not re-enable broad watchlist topics.
- `backend/services/collector.py`: call account collection in today's daily *collection* stage so the existing quick-read pass sees account items. If event radar exists, it subsequently sees the same account items in its one batch.
- `backend/services/briefing_generator.py`, `backend/services/storage.py`, `frontend/src/pages/BriefingPage.jsx`, `frontend/src/pages/dailySignalData.js`: locally expose saved `signals.accounts` and `signals.account_status` and render account cards alongside Events when available.
- Tests: `backend/tests/test_x_public_profile.py`, `backend/tests/test_x_account_daily.py`, `backend/tests/test_x_account_briefing.py`, `frontend/src/pages/dailySignalData.test.mjs`, `frontend/tests/accountRadar.browser.test.mjs`.

---

### Task 1: Public profile feasibility gate and strict offline parser

**Files:** Create `backend/services/x_public_profile.py`, `backend/tests/test_x_public_profile.py`; update `README.md` only with observed limitations, not scraped post content.

**Interfaces:** Produces the two profile functions above. The read-only anonymous preflight is a **stop gate**, not permission to scrape protected endpoints. Preliminary check (2026-10-13) saw public `x.com/oran_ge` return HTTP 200 with top-level posts, nested quoted posts, and status links, but no `<time>` tags; the public syndication endpoint returned 429 and RSSHub timed out. This **does not establish** stable coverage or a reliable reply/quote classifier.

- [ ] **Step 1: Run one anonymous read-only GET per account and capture only status, article/status-link counts and whether author/type/date can be verified; do not store live bodies or use credentials.** Verify original and quote structures against the rendered profile, and UTC dates against an independent rendered time marker. Status IDs may encode creation time using UTC milliseconds `(int(id) >> 22) + 1288834974657` but **must not** be assumed valid until verified against visible time for that post. If none of the four accounts has classifiable content, stop this plan, report `unavailable` to the user, and continue the independent event radar plan. If originals work but quotes cannot be classified, tell the user coverage is partial and ask whether to ship original-only coverage before proceeding to Task 2; do not claim quote following works.
- [ ] **Step 2: Write failing offline tests** from a **minimal sanitized HTML fixture** matching the observed public DOM: an outer `<article>` with `@oran_ge` and `/oran_ge/status/2109821043506610569`, one nested `<article>` for a different author; a second outer original, a `Replying to` article, and a `reposted` label. Assert exactly the original and the outer quote, not the nested quoted author's post, reply, or pure repost:

```python
result = parse_public_profile(html_fixture, 'oran_ge', '2026-10-13')
assert [post['metadata']['post_type'] for post in result['posts']] == ['quote', 'original']
assert all(post['metadata']['account'] == '@oran_ge' for post in result['posts'])
assert result['posts'][0]['metadata']['quoted_url'].startswith('https://x.com/')
```
 Assert the real ID above maps to `2026-10-13T01:38:30` UTC, and an HTML document with a login screen or no verifiable article is `unavailable` rather than `no_posts`. Assert a valid page explicitly stating the account has no posts can return `ok` with an empty posts list; failure to find posts is not that signal. Mock 429/403 as unavailable and `httpx.ReadTimeout` as unavailable; parser must not rely on local wall-clock time for publication.
- [ ] **Step 3: Verify RED.** `cd backend && source venv/bin/activate && python -m pytest tests/test_x_public_profile.py -q` fails on missing module.
- [ ] **Step 4: Implement minimum parser and adapter.** Validate `handle` with `re.fullmatch(r'[A-Za-z0-9_]{1,15}', handle)`. For each **outer** article, require a status anchor under that handle, check displayed author, derive and validate UTC timestamp from status ID against the preflight evidence; use nested foreign-author article only to classify and attribute a quote:

```python
articles = [a for a in BeautifulSoup(html, 'html.parser').select('article') if a.find_parent('article') is None]
posted_at = datetime.fromtimestamp(((int(status_id) >> 22) + 1288834974657) / 1000, timezone.utc)
if posted_at.date() > date.fromisoformat(day) or posted_at.date() < date.fromisoformat(day) - timedelta(days=2):
    continue
```
 Reject ambiguous or absent post-type markers instead of treating every article as an original. Retain original text, original URL, quoted URL (for quotes), `metadata.origin='x_public_account'`, `metadata.account='@oran_ge'`, `metadata.post_type='original'|'quote'`, `published_at` and `created_at=day`. HTTP request has 8-second timeout, a transparent User-Agent, no cookies, no retries around access controls. Status `partial` if some articles are ambiguous but valid items remain.
- [ ] **Step 5: Verify GREEN.** Run targeted pytest and check one browser HTML sample for changes **without saving or committing user-specific data**. Commit parser, tests, and README limitation note with message `feat: parse verifiable public X account posts`. Do not commit if the gate failed; report the blocker instead.

### Task 2: Current-day account collection, durable coverage and deduplication

**Files:** Create `backend/services/x_account_daily.py`, `backend/tests/test_x_account_daily.py`; modify `backend/config/collector.yaml`, `backend/services/collector.py` and `backend/tests/test_collector_daily.py`.

**Interfaces:** Consumes `fetch_public_profile` from Task 1. `load_x_account_day(day)` reads only `data/account_runs/{day}.json`. Per-handle saved record: `{status, checked_at, reason, posts:[{id,url,title,summary,published_at,metadata:{account,post_type,...}}]}`. `store_content_items` keeps only new verified raw posts; cached account page can still include a newly verified post whose canonical URL had already appeared as a last30days import without inserting a duplicate content row.

- [ ] **Step 1: Write failing tests** with `tmp_path`, patched `_load_content_file`, `store_content_items`, and a fake profile client: four accounts return independently `(ok:one original, partial:one quote, unavailable:429, ok:verified empty)`; assert all four statuses saved and only two genuine posts inserted. Re-run same day: no duplicate content, no additional network calls for successful handles. Repeated or `@`-prefixed config handles normalize to one `@handle` and trigger one request. Load yesterday's `x-account-2109821043506610569`: today's identical post must not be reinserted; a new quote can be inserted. A successful save must use atomic replacement and must not wipe a previous good cache when another handle times out:

```python
saved = load_x_account_day('2026-10-13')
assert saved['accounts']['@oran_ge']['status'] == 'ok'
assert saved['accounts']['@fkysly']['status'] == 'unavailable'
assert len(saved['accounts']['@dotey']['posts']) == 1
```
 A historical date must not make any live HTTP call; inject or patch a deterministic current-day clock for this test so it passes after 2026-10-13.
- [ ] **Step 2: Verify RED.** `cd backend && source venv/bin/activate && python -m pytest tests/test_x_account_daily.py tests/test_collector_daily.py -q` fails on absent integration.
- [ ] **Step 3: Implement bounded collection.** Normalize and deduplicate configured handles before fetching; start with the four named handles but allow the validated config list to be edited (max 20 handles), limit to five recent posts per account (publication within day-2 .. day inclusive), and use a semaphore of 2; skip already-successful cached handles on rerun and retry only previously unavailable ones with a per-run cap. Use canonical URL plus status ID for same-day and previous-two-day dedup; preserve existing imported raw items and existing `data/content` files. Write state JSON via temp-file + `os.replace`; write state even on failure:

```python
path = cache_dir / f'{day}.json'
tmp = path.with_suffix('.tmp')
tmp.write_text(json.dumps({'accounts': accounts}, ensure_ascii=False), encoding='utf-8')
os.replace(tmp, path)
```
 Wire `run_collection(target_date=day)` to account collection only when `day` is today's date and config is enabled; the direct `run_x_account_daily` entry point must also guard historical dates rather than relying solely on its caller. Preserve the old opt-in watchlist setting and place this before quick-read batching. No live request for historic backfill.
- [ ] **Step 4: Verify GREEN.** Targeted tests and `python -m pytest tests/test_watchlist_daily.py tests/test_anthropic_blog_integration.py -q`.
- [ ] **Step 5: Commit** only the named task files with `git commit -m "feat: cache followed public X account status"`.

### Task 3: Saved account API and account-first briefing view

**Files:** Modify `backend/services/briefing_generator.py`, `backend/services/storage.py`, `frontend/src/pages/BriefingPage.jsx`, `frontend/src/pages/dailySignalData.js`, `frontend/src/pages/dailySignalData.test.mjs`, `README.md`; create `backend/tests/test_x_account_briefing.py`, `frontend/tests/accountRadar.browser.test.mjs`.

**Interfaces:** Consumes `load_x_account_day(day)` without any network or LLM. `signals.accounts` follows the approved grouped contract: `[{handle, status, checked_at, reason, posts:[{id, kind, url, title, takeaway, published_at, quoted_url?}]}]`; each configured handle appears even when its `posts` is empty. Preserve the original `signals.inspiration/execution/total` fields. If the event plan is installed, default signal view contains both `关注账号` and `事件追踪`; if not, it shows Accounts plus existing legacy dual-track signals and All Content. Old dates lacking new account keys use legacy rendering.

- [ ] **Step 1: Write failing API and UI tests.** Backend: a saved original and quote appear exactly once under their respective `signals.accounts[*].posts`, with original links and post types; 429 account status says unavailable, while a verified empty account says ok with zero posts. Assert `items` and legacy tracks are unchanged and the API GET never calls `fetch_public_profile` or the selection LLM. If a day has only saved account failure state (no content), the date is discoverable and a briefing shows that failure instead of 404. Frontend unit: `getAccountItems({signals:{accounts:[{handle:'@dotey',status:'ok',posts:[{id:'x-1'}]}]}})` returns that group and returns `[]` for an old snapshot. Browser: mock a cached briefing and verify the 关注账号 tab displays source link, quote label, account handle and honest failure message, then 全部内容 still shows raw items; test a legacy briefing still renders old signal tabs:

```js
await page.getByRole('button', { name: /关注账号/ }).click()
await page.getByRole('link', { name: /查看原帖/ }).waitFor()
await page.getByText(/采集不可用/).waitFor()
await page.getByRole('button', { name: /全部内容/ }).click()
```

- [ ] **Step 2: Verify RED.** Run `cd backend && source venv/bin/activate && python -m pytest tests/test_x_account_briefing.py -q`, `cd frontend && node --test src/pages/dailySignalData.test.mjs`, and browser test with a Vite server on an unoccupied port (`SIGNAL_FEED_TEST_URL=http://127.0.0.1:5176 node --test tests/accountRadar.browser.test.mjs` (start Vite in `frontend` with `npm run dev -- --host 127.0.0.1 --port 5176` after checking port availability; shut it down afterwards)).
- [ ] **Step 3: Implement purely local read/view.** `generate_briefing_for_date(day)` reads saved account state, preserves old `signals` keys, and includes grouped `signals.accounts` only for dates with recorded account state:

```python
saved = load_x_account_day(date)
if saved:
    briefing['signals']['accounts'] = [
        {'handle': handle, 'status': run['status'], 'checked_at': run['checked_at'],
         'reason': run['reason'], 'posts': [make_account_card(post, quick_reads) for post in run['posts']]}
        for handle, run in saved['accounts'].items()
    ]
```

Here `quick_reads = load_quick_reads(date)` is loaded before building the groups. Define `make_account_card(post: dict, quick_reads: dict[str, str]) -> dict` in `backend/services/briefing_generator.py` to map `post_type` to `kind`, include the original URL and optional quoted URL, and use saved quick-read text if available. Add a status-only date to `get_all_dates()` without turning manual-import-only days into daily dates. Compute account excerpt from saved quick read when available, otherwise truncate the stored post body and label it as original excerpt, not a model opinion. View tabs display 关注账号 and (if present) 事件追踪; tabs switch client-side without search. The user can always access 全部内容; status `unavailable` must not read “该账号今日没有发帖.” Static snapshots use the same GET payload, with no extra build-time search.
- [ ] **Step 4: Verify GREEN** targeted tests, `cd backend && source venv/bin/activate && python -m pytest tests/ -q`, `cd frontend && node --test src/**/*.test.mjs src/*.test.mjs && npm run build`, the browser test and `git diff --check`. Manual online smoke check is read-only/optional and is not proof of complete X coverage; do not run real daily ingestion/model calls without user authorization.
- [ ] **Step 5: Commit** only the paths in this task with `git commit -m "feat: show followed accounts with honest coverage"`. Verify unrelated working-tree state was not staged.
