# Venture Product Radar Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a SignalForge Venture Radar page that imports raw `venture-product-radar.v2` JSON reports, stores them as report archives, and renders products, funding rounds, signals, evidence, and follow-up work.

**Architecture:** Add a focused backend report storage service under `data/venture_radar`, extend the existing venture radar router with report archive endpoints, and add a React page that consumes those endpoints. The page renders the raw report shape directly instead of relying on `data/content` content items.

**Tech Stack:** FastAPI, Python unittest, file-backed JSON storage, React, Vite, React Router, Node `node:test` source assertions.

---

## File Structure

- Create `backend/services/venture_radar_reports.py`: owns validation, import, index persistence, report loading, and report summaries.
- Create `backend/tests/test_venture_radar_reports.py`: unit tests for import/list/load behavior and validation errors.
- Modify `backend/routers/venture_radar.py`: add `/reports`, `/reports/{id}`, and `/import-file` endpoints; keep existing research endpoints.
- Modify `backend/tests/test_venture_radar_router.py`: router tests for report archive endpoints.
- Create `frontend/src/pages/VentureRadarPage.jsx`: report archive UI, import form, tabs, filtering, and detail panel.
- Create `frontend/src/pages/VentureRadarPage.test.mjs`: source assertions for required endpoints and report fields.
- Modify `frontend/src/App.jsx`: register `/venture-radar`.
- Modify `frontend/src/components/Sidebar.jsx`: add sidebar entry.
- Modify `frontend/src/index.css`: add scoped Venture Radar styles if page-local styles are not sufficient.

## Task 1: Backend Report Storage

**Files:**
- Create: `backend/services/venture_radar_reports.py`
- Create: `backend/tests/test_venture_radar_reports.py`

- [ ] **Step 1: Write failing storage tests**

Create `backend/tests/test_venture_radar_reports.py`:

```python
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import venture_radar_reports as reports


SAMPLE_REPORT = {
    "schema_version": "venture-product-radar.v2",
    "command": "venture-radar",
    "mode": "radar",
    "topic": "AI sales automation startup opportunities",
    "generated_at": "2026-07-08T13:47:59+00:00",
    "lookback_days": 30,
    "companies": [],
    "products": [{"name": "JSONbored/awesome-claude", "confidence": "low"}],
    "funding_rounds": [{"company_name": "AI chip maker SambaNova", "amount": "$1B"}],
    "signals": [{"title": "Railway secures $100 million", "signal_score": 57}],
    "source_links": [{"url": "https://example.com/source"}],
    "next_watch_items": ["Find primary product page for JSONbored/awesome-claude."],
    "errors_by_source": {"rss_feeds": ["HTTP Error 403: Forbidden"]},
}


class VentureRadarReportsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        reports.VENTURE_RADAR_DIR = self.data_dir
        reports.REPORTS_DIR = self.data_dir / "reports"
        reports.INDEX_FILE = self.data_dir / "index.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_report(self, name="radar-ai-sales-automation-startup-opportunities-20260708T134819Z.json", data=None):
        path = self.data_dir / name
        path.write_text(json.dumps(data or SAMPLE_REPORT, ensure_ascii=False), encoding="utf-8")
        return path

    def test_import_report_copies_raw_json_and_indexes_summary(self):
        entry = reports.import_venture_radar_report(str(self._write_report()))

        self.assertEqual(entry["id"], "radar-ai-sales-automation-startup-opportunities-20260708T134819Z")
        self.assertEqual(entry["topic"], "AI sales automation startup opportunities")
        self.assertEqual(entry["counts"]["products"], 1)
        self.assertEqual(entry["counts"]["funding_rounds"], 1)
        self.assertEqual(entry["counts"]["signals"], 1)
        self.assertEqual(entry["counts"]["source_links"], 1)
        self.assertEqual(entry["counts"]["next_watch_items"], 1)
        self.assertEqual(entry["counts"]["source_errors"], 1)

        stored = reports.load_venture_radar_report(entry["id"])
        self.assertEqual(stored["topic"], SAMPLE_REPORT["topic"])
        self.assertEqual(stored["products"][0]["name"], "JSONbored/awesome-claude")

    def test_list_reports_orders_by_generated_at_desc(self):
        older = dict(SAMPLE_REPORT, topic="Older", generated_at="2026-07-07T00:00:00+00:00")
        newer = dict(SAMPLE_REPORT, topic="Newer", generated_at="2026-07-09T00:00:00+00:00")
        reports.import_venture_radar_report(str(self._write_report("older.json", older)))
        reports.import_venture_radar_report(str(self._write_report("newer.json", newer)))

        listed = reports.list_venture_radar_reports()

        self.assertEqual([item["topic"] for item in listed], ["Newer", "Older"])

    def test_rejects_invalid_schema(self):
        bad = dict(SAMPLE_REPORT, schema_version="other.v1")
        with self.assertRaises(ValueError):
            reports.import_venture_radar_report(str(self._write_report("bad.json", bad)))

    def test_rejects_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            reports.import_venture_radar_report(str(self.data_dir / "missing.json"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run storage test to verify RED**

Run:

```bash
python3 -m unittest backend.tests.test_venture_radar_reports -v
```

Expected: FAIL or ERROR because `services.venture_radar_reports` does not exist.

- [ ] **Step 3: Implement storage service**

Create `backend/services/venture_radar_reports.py` with:

```python
"""Raw venture-product-radar report storage."""
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from services.storage import DATA_DIR


VENTURE_RADAR_DIR = DATA_DIR / "venture_radar"
REPORTS_DIR = VENTURE_RADAR_DIR / "reports"
INDEX_FILE = VENTURE_RADAR_DIR / "index.json"


def _ensure_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> Dict:
    _ensure_dirs()
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return {"reports": []}


def _save_index(index: Dict) -> None:
    _ensure_dirs()
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _report_id_from_path(path: Path) -> str:
    stem = path.stem.strip()
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip("-") or "venture-radar-report"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_source_errors(report: Dict) -> int:
    errors = report.get("errors_by_source") or {}
    if not isinstance(errors, dict):
        return 0
    return sum(len(v) if isinstance(v, list) else 1 for v in errors.values())


def _validate_report(report: Dict) -> None:
    if not isinstance(report, dict):
        raise ValueError("venture radar report must be a JSON object")
    schema = str(report.get("schema_version") or "")
    if not schema.startswith("venture-product-radar."):
        raise ValueError("schema_version must start with venture-product-radar.")
    if not str(report.get("topic") or "").strip():
        raise ValueError("topic required")


def summarize_venture_radar_report(report: Dict, report_id: str = "", source_path: str = "") -> Dict:
    return {
        "id": report_id,
        "topic": report.get("topic", ""),
        "mode": report.get("mode", "radar"),
        "command": report.get("command", ""),
        "generated_at": report.get("generated_at", ""),
        "lookback_days": report.get("lookback_days", 0),
        "counts": {
            "companies": len(report.get("companies") or []),
            "products": len(report.get("products") or []),
            "funding_rounds": len(report.get("funding_rounds") or []),
            "signals": len(report.get("signals") or []),
            "source_links": len(report.get("source_links") or []),
            "next_watch_items": len(report.get("next_watch_items") or []),
            "source_errors": _count_source_errors(report),
        },
        "source_path": source_path,
        "imported_at": _now_iso(),
    }


def import_venture_radar_report(path: str) -> Dict:
    source = Path(path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"venture radar report not found: {source}")
    report = json.loads(source.read_text(encoding="utf-8"))
    _validate_report(report)

    _ensure_dirs()
    report_id = _report_id_from_path(source)
    target = REPORTS_DIR / f"{report_id}.json"
    shutil.copyfile(source, target)

    entry = summarize_venture_radar_report(report, report_id=report_id, source_path=str(source))
    index = _load_index()
    reports = [item for item in index.get("reports", []) if item.get("id") != report_id]
    reports.append(entry)
    index["reports"] = sorted(reports, key=lambda item: item.get("generated_at", ""), reverse=True)
    _save_index(index)
    return entry


def list_venture_radar_reports() -> List[Dict]:
    index = _load_index()
    return sorted(index.get("reports", []), key=lambda item: item.get("generated_at", ""), reverse=True)


def load_venture_radar_report(report_id: str) -> Optional[Dict]:
    safe_id = _report_id_from_path(Path(report_id))
    path = REPORTS_DIR / f"{safe_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run storage test to verify GREEN**

Run:

```bash
python3 -m unittest backend.tests.test_venture_radar_reports -v
```

Expected: PASS.

## Task 2: Backend Router Endpoints

**Files:**
- Modify: `backend/routers/venture_radar.py`
- Modify: `backend/tests/test_venture_radar_router.py`

- [ ] **Step 1: Write failing router tests**

Append tests to `backend/tests/test_venture_radar_router.py`:

```python
    def test_import_file_and_read_report_archive(self):
        from services import venture_radar_reports as reports
        reports.VENTURE_RADAR_DIR = Path(self._tmp.name) / "venture_radar"
        reports.REPORTS_DIR = reports.VENTURE_RADAR_DIR / "reports"
        reports.INDEX_FILE = reports.VENTURE_RADAR_DIR / "index.json"

        sample = {
            "schema_version": "venture-product-radar.v2",
            "command": "venture-radar",
            "mode": "radar",
            "topic": "AI sales automation startup opportunities",
            "generated_at": "2026-07-08T13:47:59+00:00",
            "lookback_days": 30,
            "products": [{"name": "JSONbored/awesome-claude"}],
            "funding_rounds": [{"company_name": "AI chip maker SambaNova", "amount": "$1B"}],
            "signals": [{"title": "Railway secures $100 million"}],
            "source_links": [],
            "next_watch_items": [],
        }
        path = Path(self._tmp.name) / "sample-report.json"
        path.write_text(json.dumps(sample), encoding="utf-8")

        imported = self.client.post("/api/venture-radar/import-file", json={"path": str(path)})
        self.assertEqual(imported.status_code, 200)
        report_id = imported.json()["id"]

        listed = self.client.get("/api/venture-radar/reports")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["reports"][0]["id"], report_id)

        loaded = self.client.get(f"/api/venture-radar/reports/{report_id}")
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["topic"], "AI sales automation startup opportunities")

    def test_unknown_report_returns_404(self):
        r = self.client.get("/api/venture-radar/reports/nope")
        self.assertEqual(r.status_code, 404)
```

Also add `import json` at the top of that test file.

- [ ] **Step 2: Run router tests to verify RED**

Run:

```bash
python3 -m unittest backend.tests.test_venture_radar_router -v
```

Expected: FAIL because the new archive endpoints do not exist.

- [ ] **Step 3: Implement router endpoints**

Update `backend/routers/venture_radar.py`:

```python
from services.venture_radar_reports import (
    import_venture_radar_report,
    list_venture_radar_reports,
    load_venture_radar_report,
)
```

Add endpoints before `@router.get("/research/{job_id}")`:

```python
@router.get("/reports")
async def reports_index():
    return {"reports": list_venture_radar_reports()}


@router.get("/reports/{report_id}")
async def report_detail(report_id: str):
    report = load_venture_radar_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    return report


@router.post("/import-file")
async def import_report_file(request: dict):
    path = (request.get("path") or "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="path required")
    try:
        return import_venture_radar_report(path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
```

- [ ] **Step 4: Run router tests to verify GREEN**

Run:

```bash
python3 -m unittest backend.tests.test_venture_radar_router -v
```

Expected: PASS.

## Task 3: Frontend Venture Radar Page

**Files:**
- Create: `frontend/src/pages/VentureRadarPage.jsx`
- Create: `frontend/src/pages/VentureRadarPage.test.mjs`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write failing frontend source test**

Create `frontend/src/pages/VentureRadarPage.test.mjs`:

```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./VentureRadarPage.jsx', import.meta.url), 'utf8')

test('VentureRadarPage uses report archive endpoints', () => {
  assert.match(source, /\/api\/venture-radar\/reports/)
  assert.match(source, /\/api\/venture-radar\/import-file/)
  assert.match(source, /\/api\/venture-radar\/research/)
})

test('VentureRadarPage renders the required report tabs', () => {
  for (const label of ['产品线索', '融资动态', '市场信号', '来源证据', '下一步跟踪']) {
    assert.match(source, new RegExp(label))
  }
})

test('VentureRadarPage handles raw venture-product-radar fields', () => {
  for (const field of [
    'products',
    'funding_rounds',
    'signals',
    'source_links',
    'next_watch_items',
    'research_plan',
    'errors_by_source',
    'company_name',
    'traction_signals',
    'signal_score',
  ]) {
    assert.match(source, new RegExp(field))
  }
})

test('VentureRadarPage strips HTML summaries before rendering', () => {
  assert.match(source, /stripHtml/)
  assert.doesNotMatch(source, /dangerouslySetInnerHTML/)
})
```

- [ ] **Step 2: Run frontend test to verify RED**

Run:

```bash
node --test frontend/src/pages/VentureRadarPage.test.mjs
```

Expected: FAIL because `VentureRadarPage.jsx` does not exist.

- [ ] **Step 3: Implement page and routing**

Create `frontend/src/pages/VentureRadarPage.jsx` with a compact implementation that:

- loads `GET /api/venture-radar/reports` on mount;
- imports local JSON with `POST /api/venture-radar/import-file`;
- starts research with `POST /api/venture-radar/research`;
- polls `GET /api/venture-radar/research/{job_id}`;
- renders tabs for products, funding, signals, sources, and watch items;
- filters by keyword and confidence;
- strips HTML summaries with `stripHtml`.

Modify `frontend/src/App.jsx`:

```jsx
import VentureRadarPage from './pages/VentureRadarPage'
// ...
<Route path="/venture-radar" element={<VentureRadarPage />} />
```

Modify `frontend/src/components/Sidebar.jsx`:

```jsx
<Link to="/venture-radar" className={`menu-item ${isActive('/venture-radar') ? 'active' : ''}`}>
  <span>🛰️</span><span>创投产品雷达</span>
</Link>
```

- [ ] **Step 4: Run frontend test to verify GREEN**

Run:

```bash
node --test frontend/src/pages/VentureRadarPage.test.mjs
```

Expected: PASS.

## Task 4: Full Verification

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run targeted backend tests**

Run:

```bash
python3 -m unittest backend.tests.test_venture_radar_reports backend.tests.test_venture_radar_router -v
```

Expected: PASS.

- [ ] **Step 2: Run targeted frontend tests**

Run:

```bash
node --test frontend/src/pages/VentureRadarPage.test.mjs frontend/src/staticBuild.test.mjs
```

Expected: PASS.

- [ ] **Step 3: Verify changed file status**

Run:

```bash
git status --short backend/services/venture_radar_reports.py backend/routers/venture_radar.py backend/tests/test_venture_radar_reports.py backend/tests/test_venture_radar_router.py frontend/src/pages/VentureRadarPage.jsx frontend/src/pages/VentureRadarPage.test.mjs frontend/src/App.jsx frontend/src/components/Sidebar.jsx frontend/src/index.css docs/superpowers/plans/2026-07-09-venture-product-radar-page.md
```

Expected: only the files in this feature show as changed.

## Self-Review

- Spec coverage: backend raw report storage, report archive endpoints, local JSON import, report tabs, filtering, detail rendering, and sample JSON acceptance are covered.
- Placeholder scan: no task uses open-ended implementation placeholders.
- Type consistency: backend report id, counts, and field names match the confirmed design and sample `venture-product-radar.v2` schema.
