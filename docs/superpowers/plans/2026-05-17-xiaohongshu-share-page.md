# Xiaohongshu Share Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Xiaohongshu-ready three-page share artifact from existing SignalForge opportunity, briefing, and quick-read data.

**Architecture:** Add a focused backend service that selects and normalizes share data, a renderer that turns the payload into standalone HTML, and a CLI command that writes the HTML artifact for a chosen date. Keep selection and rendering independent so the same payload can later be reused by PNG export or an API endpoint without coupling to the current frontend.

**Tech Stack:** Python 3, existing file-based data storage, HTML/CSS template rendering, `unittest`.

---

## File Structure

- Create `backend/services/share_page.py`
  - Owns payload assembly, opportunity normalization, briefing selection, quick-read attachment, and HTML rendering.
- Modify `backend/cli.py`
  - Adds a `share-page` command that generates the HTML artifact for a chosen date.
- Create `backend/tests/test_share_page.py`
  - Covers selection rules, quick-read attachment, and rendered HTML structure.
- Create `backend/docs/share-pages/.gitkeep`
  - Keeps the generated-output directory present without committing generated HTML files.

### Task 1: Normalize Xiaohongshu Share Payload

**Files:**
- Create: `backend/services/share_page.py`
- Test: `backend/tests/test_share_page.py`

- [ ] **Step 1: Write the failing tests**

```python
import unittest

from backend.services.share_page import build_share_payload


class SharePayloadTest(unittest.TestCase):
    def test_build_share_payload_selects_top_opportunities_and_diverse_briefings(self):
        opportunities = [
            {"opportunity_title": "Low", "total_score": 10, "core_insight": "low", "product_form": "low"},
            {"opportunity_title": "Top A", "total_score": 18, "core_insight": "a", "product_form": "a"},
            {"opportunity_title": "Top B", "total_score": 17, "core_insight": "b", "product_form": "b"},
            {"opportunity_title": "Top C", "total_score": 16, "core_insight": "c", "product_form": "c"},
        ]
        items = [
            {"id": "repo-1", "title": "Repo 1", "source": "GitHub", "source_type": "repo", "relevance_score": 9},
            {"id": "repo-2", "title": "Repo 2", "source": "GitHub", "source_type": "repo", "relevance_score": 8},
            {"id": "paper-1", "title": "Paper 1", "source": "HF", "source_type": "paper", "relevance_score": 8},
            {"id": "blog-1", "title": "Blog 1", "source": "OpenAI", "source_type": "blog", "relevance_score": 8},
            {"id": "model-1", "title": "Model 1", "source": "HF", "source_type": "model", "relevance_score": 8},
            {"id": "wechat-1", "title": "Wechat 1", "source": "WX", "source_type": "wechat", "relevance_score": 8},
        ]
        quick_reads = {item["id"]: f"quick-{item['id']}" for item in items}

        payload = build_share_payload("2026-05-14", opportunities, items, quick_reads)

        self.assertEqual([i["title"] for i in payload["opportunities"]], ["Top A", "Top B", "Top C"])
        self.assertEqual(
            [i["id"] for i in payload["briefings"]],
            ["repo-1", "paper-1", "blog-1", "model-1", "wechat-1"],
        )
        self.assertEqual(payload["briefings"][0]["quick_read"], "quick-repo-1")

    def test_build_share_payload_skips_items_without_quick_reads(self):
        payload = build_share_payload(
            "2026-05-14",
            [],
            [
                {"id": "repo-1", "title": "Repo 1", "source": "GitHub", "source_type": "repo", "relevance_score": 9},
                {"id": "paper-1", "title": "Paper 1", "source": "HF", "source_type": "paper", "relevance_score": 8},
            ],
            {"paper-1": "paper quick"},
        )

        self.assertEqual([i["id"] for i in payload["briefings"]], ["paper-1"])
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest backend.tests.test_share_page
```

Expected:

```text
ModuleNotFoundError: No module named 'backend.services.share_page'
```

- [ ] **Step 3: Implement the minimal payload builder**

```python
from typing import Dict, List


def build_share_payload(
    date: str,
    opportunities: List[Dict],
    content_items: List[Dict],
    quick_reads: Dict[str, str],
    opportunity_limit: int = 3,
    briefing_limit: int = 5,
) -> Dict:
    ranked_opportunities = sorted(
        opportunities,
        key=lambda item: item.get("total_score", 0),
        reverse=True,
    )[:opportunity_limit]

    normalized_opportunities = [
        {
            "title": item.get("opportunity_title") or item.get("title") or "未命名商业机会",
            "score": item.get("total_score", 0),
            "summary": _compact_opportunity_summary(item),
        }
        for item in ranked_opportunities
    ]

    ranked_items = sorted(
        (item for item in content_items if item.get("id") in quick_reads),
        key=lambda item: item.get("relevance_score", 0),
        reverse=True,
    )
    selected_items = _select_diverse_items(ranked_items, briefing_limit)
    normalized_briefings = [
        {
            "id": item["id"],
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "source_type": item.get("source_type", "news"),
            "quick_read": quick_reads[item["id"]],
        }
        for item in selected_items
    ]

    return {
        "date": date,
        "opportunities": normalized_opportunities,
        "briefings": normalized_briefings,
    }


def _compact_opportunity_summary(item: Dict) -> str:
    return item.get("product_form") or item.get("core_insight") or ""


def _select_diverse_items(items: List[Dict], limit: int) -> List[Dict]:
    selected = []
    selected_ids = set()
    selected_types = set()

    if items:
        selected.append(items[0])
        selected_ids.add(items[0]["id"])
        selected_types.add(_briefing_type(items[0]))

    for item in items:
        item_type = _briefing_type(item)
        if item["id"] in selected_ids or item_type in selected_types:
            continue
        selected.append(item)
        selected_ids.add(item["id"])
        selected_types.add(item_type)
        if len(selected) >= limit:
            return selected

    for item in items:
        if item["id"] in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(item["id"])
        if len(selected) >= limit:
            break

    return selected


def _briefing_type(item: Dict) -> str:
    if item.get("source_type") == "hackernews" or item.get("source") == "HackerNews Daily":
        return "hackernews"
    return item.get("source_type", "news")
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
python3 -m unittest backend.tests.test_share_page
```

Expected:

```text
Ran 2 tests
OK
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/share_page.py backend/tests/test_share_page.py
git commit -m "feat: build xiaohongshu share payload"
```

### Task 2: Render the Three-Page HTML Artifact

**Files:**
- Modify: `backend/services/share_page.py`
- Test: `backend/tests/test_share_page.py`

- [ ] **Step 1: Add failing renderer tests**

```python
from backend.services.share_page import render_share_page_html


class ShareRenderTest(unittest.TestCase):
    def test_render_share_page_html_builds_three_pages(self):
        payload = {
            "date": "2026-05-14",
            "opportunities": [
                {"title": "A", "score": 18, "summary": "alpha"},
                {"title": "B", "score": 17, "summary": "beta"},
                {"title": "C", "score": 16, "summary": "gamma"},
            ],
            "briefings": [
                {"id": f"i-{n}", "title": f"Item {n}", "source_type": "repo", "quick_read": f"quick {n}"}
                for n in range(1, 6)
            ],
        }

        html = render_share_page_html(payload)

        self.assertEqual(html.count('class="xhs-page'), 3)
        self.assertIn("今天最值得看的 3 个 AI 商业机会", html)
        self.assertIn("今天值得继续跟踪的 AI 情报 01", html)
        self.assertIn("今天值得继续跟踪的 AI 情报 02", html)
        self.assertIn("quick 5", html)
```

- [ ] **Step 2: Run the renderer test and verify it fails**

Run:

```bash
python3 -m unittest backend.tests.test_share_page.ShareRenderTest
```

Expected:

```text
ImportError: cannot import name 'render_share_page_html'
```

- [ ] **Step 3: Implement the minimal renderer**

```python
from html import escape


def render_share_page_html(payload: Dict) -> str:
    opportunities = payload["opportunities"]
    briefings = payload["briefings"]
    briefing_pages = [briefings[:3], briefings[3:5]]

    opportunity_cards = "".join(
        f"""
        <article class="xhs-item">
          <div class="xhs-headline">
            <span class="xhs-rank">{index}</span>
            <h4>{escape(item["title"])}</h4>
            <span class="xhs-score">{item["score"]} / 20</span>
          </div>
          <p>{escape(item["summary"])}</p>
        </article>
        """
        for index, item in enumerate(opportunities, 1)
    )

    briefing_sections = "".join(
        _render_briefing_page(page_items, page_index)
        for page_index, page_items in enumerate(briefing_pages, start=1)
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>SignalForge Xiaohongshu Share</title>
  <style>{_SHARE_PAGE_CSS}</style>
</head>
<body>
  <main class="xhs-stage">
    <section class="xhs-page">
      <div class="xhs-kicker">Page 1 / Business</div>
      <h1>今天最值得看的 3 个 AI 商业机会</h1>
      <div class="xhs-list">{opportunity_cards}</div>
      <footer><span>SignalForge</span><span>{escape(payload["date"])}</span></footer>
    </section>
    {briefing_sections}
  </main>
</body>
</html>"""


def _render_briefing_page(items: List[Dict], page_index: int) -> str:
    cards = "".join(
        f"""
        <article class="xhs-item quick-card">
          <div class="xhs-headline">
            <span class="xhs-rank">{rank}</span>
            <h4>{escape(item["title"])}</h4>
            <span class="xhs-score">{escape(item["source_type"])}</span>
          </div>
          <div class="quick-copy">{_markdown_to_html(item["quick_read"])}</div>
        </article>
        """
        for rank, item in enumerate(items, 1 + (page_index - 1) * 3)
    )
    return f"""
    <section class="xhs-page accent-blue">
      <div class="xhs-kicker">Page {page_index + 1} / Signals</div>
      <h1>今天值得继续跟踪的 AI 情报 0{page_index}</h1>
      <div class="xhs-list">{cards}</div>
      <footer><span>SignalForge</span><span>{page_index + 1} / 3</span></footer>
    </section>
    """


def _markdown_to_html(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        if line.startswith("- "):
            lines.append(f"<li>{escape(line[2:])}</li>")
        elif line.strip():
            lines.append(f"<p>{escape(line)}</p>")
    return "".join(lines)


_SHARE_PAGE_CSS = """
body{margin:0;padding:32px;background:#f5f4f1;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
.xhs-stage{display:grid;grid-template-columns:repeat(3,360px);gap:20px}
.xhs-page{aspect-ratio:3/4;background:#fbfaf7;border:1px solid #eadfce;border-radius:18px;padding:22px;display:flex;flex-direction:column}
.xhs-kicker{font-size:12px;font-weight:700;letter-spacing:.08em;color:#9a3412}
h1{font-size:26px;line-height:1.12;margin:8px 0 14px}
.xhs-list{display:flex;flex-direction:column;gap:10px}
.xhs-item{background:white;border:1px solid #eadfce;border-radius:12px;padding:12px}
.xhs-headline{display:grid;grid-template-columns:22px 1fr auto;gap:10px;align-items:center;margin-bottom:7px}
.xhs-rank{width:22px;height:22px;border-radius:999px;background:#111827;color:white;display:grid;place-items:center;font-size:12px}
.xhs-score{font-size:11px;font-weight:700;color:#b45309}
h4{font-size:15px;line-height:1.3;margin:0}
p,li{font-size:12px;line-height:1.55;color:#374151}
footer{margin-top:auto;padding-top:14px;display:flex;justify-content:space-between;color:#6b7280;font-size:12px}
.accent-blue .xhs-kicker{color:#1d4ed8}
.accent-blue .xhs-rank{background:#1d4ed8}
.accent-blue .xhs-score{color:#2563eb}
"""
```

- [ ] **Step 4: Run the renderer test and verify it passes**

Run:

```bash
python3 -m unittest backend.tests.test_share_page.ShareRenderTest
```

Expected:

```text
Ran 1 test
OK
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/share_page.py backend/tests/test_share_page.py
git commit -m "feat: render xiaohongshu share html"
```

### Task 3: Add CLI Generation Command

**Files:**
- Modify: `backend/cli.py`
- Modify: `backend/services/share_page.py`
- Create: `backend/docs/share-pages/.gitkeep`
- Test: `backend/tests/test_share_page.py`

- [ ] **Step 1: Add a failing test for file generation**

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.services.share_page import generate_share_page


class ShareGenerationTest(unittest.TestCase):
    def test_generate_share_page_writes_html_file(self):
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "2026-05-14.html"
            with patch("backend.services.share_page._load_share_sources") as load_sources:
                load_sources.return_value = (
                    [{"opportunity_title": "A", "total_score": 18, "product_form": "alpha"}],
                    [{"id": "repo-1", "title": "Repo", "source": "GitHub", "source_type": "repo", "relevance_score": 9}],
                    {"repo-1": "**核心内容**：quick"},
                )

                generated = generate_share_page("2026-05-14", output_path)

        self.assertEqual(generated, output_path)
        self.assertTrue(output_path.exists())
        self.assertIn("今天最值得看的 3 个 AI 商业机会", output_path.read_text())
```

- [ ] **Step 2: Run the generation test and verify it fails**

Run:

```bash
python3 -m unittest backend.tests.test_share_page.ShareGenerationTest
```

Expected:

```text
ImportError: cannot import name 'generate_share_page'
```

- [ ] **Step 3: Implement file generation helpers**

```python
import json
from pathlib import Path

from .storage import CONTENT_DIR, load_quick_reads


def generate_share_page(date: str, output_path: Path) -> Path:
    opportunities, content_items, quick_reads = _load_share_sources(date)
    payload = build_share_payload(date, opportunities, content_items, quick_reads)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_share_page_html(payload), encoding="utf-8")
    return output_path


def _load_share_sources(date: str):
    opportunities_path = CONTENT_DIR.parent / "opportunities" / f"{date}.json"
    content_path = CONTENT_DIR / f"{date}.json"
    opportunities = []
    if opportunities_path.exists():
        opportunities = json.loads(opportunities_path.read_text(encoding="utf-8")).get("opportunities", [])
    content_items = json.loads(content_path.read_text(encoding="utf-8")) if content_path.exists() else []
    quick_reads = load_quick_reads(date)
    return opportunities, content_items, quick_reads
```

- [ ] **Step 4: Add the CLI command**

```python
def cmd_share_page(args):
    from pathlib import Path
    from services.share_page import generate_share_page

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(__file__).parent / "docs" / "share-pages"
    output_path = generate_share_page(date, output_dir / f"{date}.html")
    print(f"✓ Share page saved to {output_path}")
```

Add parser wiring:

```python
share_parser = subparsers.add_parser("share-page", help="生成小红书分享页 HTML")
share_parser.add_argument("--date", help="Date (YYYY-MM-DD), default today")
share_parser.set_defaults(func=cmd_share_page)
```

- [ ] **Step 5: Add the output directory placeholder**

```text
backend/docs/share-pages/.gitkeep
```

- [ ] **Step 6: Run the targeted tests**

Run:

```bash
python3 -m unittest backend.tests.test_share_page
```

Expected:

```text
Ran 4 tests
OK
```

- [ ] **Step 7: Run the CLI manually against existing data**

Run:

```bash
python3 backend/cli.py share-page --date 2026-05-14
```

Expected:

```text
✓ Share page saved to .../backend/docs/share-pages/2026-05-14.html
```

- [ ] **Step 8: Commit**

```bash
git add backend/cli.py backend/services/share_page.py backend/tests/test_share_page.py backend/docs/share-pages/.gitkeep
git commit -m "feat: generate xiaohongshu share page"
```

### Task 4: Verify Output Quality

**Files:**
- No production code changes required unless verification exposes defects.

- [ ] **Step 1: Run the full targeted verification suite**

Run:

```bash
python3 -m unittest backend.tests.test_share_page backend.tests.test_collector_daily
```

Expected:

```text
OK
```

- [ ] **Step 2: Generate the real HTML artifact**

Run:

```bash
python3 backend/cli.py share-page --date 2026-05-14
```

Expected:

```text
backend/docs/share-pages/2026-05-14.html
```

- [ ] **Step 3: Inspect the generated file**

Run:

```bash
rg -n "xhs-page|今天最值得看的 3 个 AI 商业机会|今天值得继续跟踪的 AI 情报" backend/docs/share-pages/2026-05-14.html
```

Expected:

- three `xhs-page` sections;
- one business title;
- two AI briefing titles.

- [ ] **Step 4: Open the generated artifact in a browser for visual review**

Run:

```bash
open backend/docs/share-pages/2026-05-14.html
```

Expected:

- one 3:4 opportunity page;
- two 3:4 briefing pages;
- readable content with no clipped text.

- [ ] **Step 5: Commit any verification-only fixes**

```bash
git add backend
git commit -m "fix: polish xiaohongshu share output"
```

## Self-Review

- Spec coverage:
  - payload selection: Task 1
  - three-page HTML rendering: Task 2
  - CLI generation flow: Task 3
  - final artifact verification: Task 4
- Placeholder scan:
  - no `TODO`, `TBD`, or underspecified implementation steps remain.
- Type consistency:
  - payload keys remain `date`, `opportunities`, and `briefings`;
  - briefing items consistently use `quick_read`;
  - page splitting consistently assumes 3 opportunity cards and 5 briefing cards.
