# Opportunity and Venture Data Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hide dates without opportunity data, make `data/venture_radar/` the sole persistence target for venture radar runs, and remove existing venture radar entries from `data/content/`.

**Architecture:** Add an opportunity-specific date query over the two opportunity cache directories and let the sidebar select that list only on the daily opportunity route. Stop the venture importer at the existing raw-report archive boundary, retain the current weekly archive APIs, and run a tested one-time migration that removes only `metadata.origin == "venture-product-radar"` entries from general content files.

**Tech Stack:** Python 3.11, FastAPI, `unittest`, React 18, React Router, Node test runner, file-based JSON storage.

## Global Constraints

- Do not change the venture report schema, weekly aggregation, opportunity generation, or page styling.
- Do not delete or rewrite files under `data/venture_radar/`.
- Preserve all non-venture entries and their order in `data/content/*.json`.
- Treat an opportunity date as populated only when `opportunities` or `solutions` is a non-empty list.
- Preserve unrelated dirty-worktree changes. Implementation commits are deferred because the touched files already contain user-owned uncommitted work; verify and report only the task-specific diff.

---

### Task 1: Opportunity-specific date storage and API

**Files:**
- Modify: `backend/services/storage.py`
- Modify: `backend/routers/dates.py`
- Modify: `backend/tests/test_storage_dates.py`
- Create: `backend/tests/test_dates_router.py`

**Interfaces:**
- Consumes: `OPPORTUNITIES_DIR` files shaped as `{ "opportunities": list }` and `RDEV_DIR` files shaped as `{ "solutions": list }`.
- Produces: `get_opportunity_dates() -> List[str]` and `GET /api/dates/opportunities -> { "dates": list[str] }`.

- [ ] **Step 1: Add failing storage tests for opportunity dates and venture-origin filtering**

```python
def test_excludes_dates_with_only_venture_radar_imports(self):
    _write(self.content_dir, "2026-07-20", [
        {"id": "v", "metadata": {"origin": "venture-product-radar"}},
    ])
    _write(self.content_dir, "2026-07-10", [
        {"id": "daily", "source_type": "rss"},
        {"id": "v2", "metadata": {"origin": "venture-product-radar"}},
    ])
    self.assertEqual(storage.get_all_dates(), ["2026-07-10"])

def test_opportunity_dates_require_non_empty_business_or_rdev_lists(self):
    _write_json(self.opportunities_dir / "2026-07-10.json", {"opportunities": [{"id": "b"}]})
    _write_json(self.rdev_dir / "2026-07-09.json", {"solutions": [{"id": "r"}]})
    _write_json(self.opportunities_dir / "2026-07-08.json", {"opportunities": []})
    _write_json(self.rdev_dir / "2026-07-08.json", {"solutions": []})
    _write_json(self.opportunities_dir / "2026-07-07.json", {"opportunities": "invalid"})
    self.assertEqual(storage.get_opportunity_dates(), ["2026-07-10", "2026-07-09"])
```

- [ ] **Step 2: Run storage tests and verify RED**

Run: `cd backend && python -m unittest tests.test_storage_dates -v`

Expected: failures because venture radar is still treated as daily content and `get_opportunity_dates` does not exist.

- [ ] **Step 3: Implement the minimal storage query and defensive origin filter**

```python
NON_DAILY_ORIGINS = {"last30days", "venture-product-radar"}

def _has_daily_content(date: str) -> bool:
    return any(
        (item.get("metadata") or {}).get("origin") not in NON_DAILY_ORIGINS
        for item in _load_content_file(date)
    )

def _cache_has_items(path: Path, key: str) -> bool:
    if not path.exists():
        return False
    values = json.loads(path.read_text(encoding="utf-8")).get(key)
    return isinstance(values, list) and len(values) > 0

def get_opportunity_dates() -> List[str]:
    dates = {path.stem for path in OPPORTUNITIES_DIR.glob("*.json")}
    dates.update(path.stem for path in RDEV_DIR.glob("*.json"))
    return [
        date for date in sorted(dates, reverse=True)
        if _cache_has_items(OPPORTUNITIES_DIR / f"{date}.json", "opportunities")
        or _cache_has_items(RDEV_DIR / f"{date}.json", "solutions")
    ]
```

Add the route before the existing parameterized routes:

```python
from services.storage import get_all_dates, get_opportunity_dates

@router.get("/opportunities")
async def get_dates_with_opportunities():
    return {"dates": get_opportunity_dates()}
```

- [ ] **Step 4: Add and run the dates router test**

```python
class DatesRouterTest(unittest.TestCase):
    def test_opportunity_dates_endpoint_uses_dedicated_storage_query(self):
        with patch("routers.dates.get_opportunity_dates", return_value=["2026-07-10"]):
            response = self.client.get("/api/dates/opportunities")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"dates": ["2026-07-10"]})
```

Run: `cd backend && python -m unittest tests.test_storage_dates tests.test_dates_router -v`

Expected: all tests pass.

### Task 2: Route-aware sidebar archives

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/components/Sidebar.test.mjs`

**Interfaces:**
- Consumes: `GET /api/dates`, `GET /api/dates/opportunities`, and `GET /api/venture-radar/weeks`.
- Produces: daily opportunity links built only from populated opportunity dates; briefing and venture routes keep their own archive lists.

- [ ] **Step 1: Add failing source-level regression assertions**

```javascript
test('Sidebar uses populated opportunity dates on daily opportunity routes', () => {
  assert.match(source, /fetch\('\/api\/dates\/opportunities'\)/)
  assert.match(source, /latestOpportunityDate/)
  assert.match(source, /isDailyOpportunity \? opportunityDates : dates/)
  assert.match(source, /\/daily-opportunities\/\$\{latestOpportunityDate\}/)
})
```

- [ ] **Step 2: Run the sidebar test and verify RED**

Run: `cd frontend && node --test src/components/Sidebar.test.mjs`

Expected: failure because the component has only the shared `dates` state.

- [ ] **Step 3: Implement separate opportunity date state and links**

```jsx
const [opportunityDates, setOpportunityDates] = useState([])
const isDailyOpportunity = Boolean(opportunityMatch)
const latestOpportunityDate = opportunityDates[0]?.date
const archiveDates = isDailyOpportunity ? opportunityDates : dates

useEffect(() => {
  fetch('/api/dates/opportunities')
    .then(res => res.json())
    .then(data => setOpportunityDates(
      (data.dates || []).map(date => ({ date, formattedDate: formatDate(date) }))
    ))
    .catch(() => {})
}, [])
```

Use `latestOpportunityDate` for the daily opportunity menu link and `archiveDates` for non-venture archive rendering. Keep `/api/venture-radar/weeks` and weekly links unchanged.

- [ ] **Step 4: Run the sidebar tests**

Run: `cd frontend && node --test src/components/Sidebar.test.mjs`

Expected: all tests pass.

### Task 3: Stop venture radar generic-content writes

**Files:**
- Modify: `backend/services/venture_product_radar_importer.py`
- Modify: `backend/tests/test_venture_product_radar_importer.py`
- Modify: `backend/cli.py`
- Create: `backend/tests/test_cli_venture_radar.py`

**Interfaces:**
- Consumes: a generated venture-product-radar JSON path.
- Produces: `import_venture_product_radar_file(path) -> Dict`, `run_venture_product_radar_via_wingsbot(...) -> int` where the count is one archived report, and `run_venture_product_radar_direct(...) -> {report_path, reports_archived, archive}`.

- [ ] **Step 1: Replace generic-store expectations with failing archive-only tests**

```python
def test_file_archives_report_without_storing_generic_content(self):
    with patch("services.venture_product_radar_importer.import_venture_radar_report", return_value={"id": "report"}) as archive, \
         patch("services.storage.store_content_items") as generic_store:
        result = import_venture_product_radar_file(path)
    self.assertEqual(result, {"id": "report"})
    archive.assert_called_once_with(path)
    generic_store.assert_not_called()
```

Update direct and Wingsbot tests to assert exactly one call through `import_venture_product_radar_file`, no second raw import, `reports_archived == 1`, and no `items_imported` result key.

- [ ] **Step 2: Run importer tests and verify RED**

Run: `cd backend && python -m unittest tests.test_venture_product_radar_importer -v`

Expected: failures because the importer still calls `store_content_items` and both run paths archive twice.

- [ ] **Step 3: Implement archive-only import flow**

```python
def import_venture_product_radar_file(path) -> Dict:
    return import_venture_radar_report(path)

def run_venture_product_radar_via_wingsbot(topic, sources=None, mode="radar") -> int:
    json_path = _trigger_wingsbot(topic, sources=sources, mode=mode)
    import_venture_product_radar_file(json_path)
    return 1

def run_venture_product_radar_direct(
    *,
    mode: str = "radar",
    sources: str = "all",
    lookback_days: int = 7,
    max_items: int = 30,
    output_dir: Path = VPR_OUTPUT_DIR,
) -> Dict:
    command = build_direct_venture_radar_command(
        mode=mode,
        sources=sources,
        lookback_days=lookback_days,
        max_items=max_items,
        output_dir=output_dir,
    )
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    report_path = _report_path_from_stdout(completed.stdout)
    archive = import_venture_product_radar_file(report_path)
    return {
        "report_path": str(report_path),
        "reports_archived": 1,
        "archive": archive,
    }
```

Remove the importer module's `store_content_items` dependency. Update CLI flow comments and replace `Imported content items` with `Archived reports` using `result['reports_archived']`.

- [ ] **Step 4: Add CLI output test and run importer/CLI tests**

```python
def test_cmd_venture_radar_reports_archive_count(self):
    result = {"report_path": "/tmp/report.json", "reports_archived": 1, "archive": {"id": "report"}}
    with patch("services.venture_product_radar_importer.run_venture_product_radar_direct", return_value=result), \
         patch("builtins.print") as print_mock:
        cli.cmd_venture_radar(Namespace(mode="radar", sources="all", lookback_days=7, max_items=30))
    output = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
    self.assertIn("Archived reports: 1", output)
    self.assertNotIn("Imported content items", output)
```

Run: `cd backend && python -m unittest tests.test_venture_product_radar_importer tests.test_cli_venture_radar -v`

Expected: all tests pass.

### Task 4: Tested historical content cleanup

**Files:**
- Create: `backend/scripts/cleanup_venture_radar_content.py`
- Create: `backend/tests/test_cleanup_venture_radar_content.py`
- Modify: only affected `data/content/*.json` files when the script runs.

**Interfaces:**
- Consumes: a directory containing JSON array files named `<date>.json`.
- Produces: `clean_content_dir(content_dir: Path) -> {files_changed, files_deleted, items_removed}` and a CLI that cleans the repository `data/content` directory.

- [ ] **Step 1: Write failing cleanup tests**

```python
def test_removes_only_venture_items_and_deletes_empty_files(self):
    mixed = self.content_dir / "2026-07-10.json"
    venture_only = self.content_dir / "2026-07-20.json"
    mixed.write_text(json.dumps([
        {"id": "daily", "metadata": {"origin": "-"}},
        {"id": "venture", "metadata": {"origin": "venture-product-radar"}},
    ]), encoding="utf-8")
    venture_only.write_text(json.dumps([
        {"id": "venture-2", "metadata": {"origin": "venture-product-radar"}},
    ]), encoding="utf-8")

    result = clean_content_dir(self.content_dir)

    self.assertEqual(json.loads(mixed.read_text(encoding="utf-8")), [
        {"id": "daily", "metadata": {"origin": "-"}},
    ])
    self.assertFalse(venture_only.exists())
    self.assertEqual(result, {"files_changed": 1, "files_deleted": 1, "items_removed": 2})
```

- [ ] **Step 2: Run cleanup tests and verify RED**

Run: `cd backend && python -m unittest tests.test_cleanup_venture_radar_content -v`

Expected: import failure because the cleanup script does not exist.

- [ ] **Step 3: Implement the minimal cleanup script**

```python
def clean_content_dir(content_dir: Path) -> dict:
    result = {"files_changed": 0, "files_deleted": 0, "items_removed": 0}
    for path in sorted(content_dir.glob("*.json")):
        items = json.loads(path.read_text(encoding="utf-8"))
        kept = [item for item in items if (item.get("metadata") or {}).get("origin") != "venture-product-radar"]
        removed = len(items) - len(kept)
        if not removed:
            continue
        result["items_removed"] += removed
        if kept:
            path.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
            result["files_changed"] += 1
        else:
            path.unlink()
            result["files_deleted"] += 1
    return result
```

The script's `main()` resolves `Path(__file__).parents[2] / "data" / "content"`, calls the function, and prints the three counts.

- [ ] **Step 4: Run cleanup tests, then execute the migration**

Run: `cd backend && python -m unittest tests.test_cleanup_venture_radar_content -v`

Expected: all tests pass.

Run: `python backend/scripts/cleanup_venture_radar_content.py`

Expected: nonzero `items_removed`; no files outside `data/content` are modified.

- [ ] **Step 5: Verify cleanup invariants**

Run: `rg -n '"origin": "venture-product-radar"' data/content`

Expected: exit code 1 with no matches.

Run: `git status --short -- data/venture_radar data/content`

Expected: changes only under `data/content`; `data/venture_radar` remains unchanged.

### Task 5: Full verification

**Files:**
- Verify all files changed in Tasks 1–4.

**Interfaces:**
- Consumes: completed implementation and migrated data.
- Produces: fresh evidence that targeted behavior, regression suite, and frontend build pass.

- [ ] **Step 1: Run targeted backend tests**

Run: `cd backend && python -m unittest tests.test_storage_dates tests.test_dates_router tests.test_venture_product_radar_importer tests.test_cli_venture_radar tests.test_cleanup_venture_radar_content tests.test_venture_radar_reports tests.test_venture_radar_router -v`

Expected: zero failures and zero errors.

- [ ] **Step 2: Run the full backend suite**

Run: `cd backend && python -m unittest discover -s tests -v`

Expected: zero failures and zero errors.

- [ ] **Step 3: Run frontend tests and build**

Run: `cd frontend && node --test src/**/*.test.mjs`

Expected: zero failing tests.

Run: `cd frontend && pnpm build`

Expected: Vite exits successfully.

- [ ] **Step 4: Inspect task-specific diff and data boundaries**

Run: `git diff --check`

Expected: no whitespace errors.

Run: `rg -n 'store_content_items' backend/services/venture_product_radar_importer.py`

Expected: exit code 1 with no matches.

Run: `rg -n '"origin": "venture-product-radar"' data/content`

Expected: exit code 1 with no matches.

Confirm that every changed line maps to the approved design and that unrelated dirty-worktree changes remain untouched.
