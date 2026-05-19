# Manual Intelligence Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "我的情报收藏" menu entry that lets users paste a URL, auto-fetches the content, and immediately generates quick read + business opportunity + R&D opportunity analyses.

**Architecture:** Separate storage (`data/manual_intel/items.json`) with its own router (`/api/manual-intel`). AI analysis is triggered asynchronously on create via `asyncio.create_task`. Frontend polls `GET /api/manual-intel/{id}` every 3 seconds until all three AI fields are populated.

**Tech Stack:** FastAPI, httpx, BeautifulSoup4, React, existing `chat_async` from `services/llm_client.py`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/services/storage.py` | Modify (append) | CRUD for manual_intel items |
| `backend/routers/manual_intel.py` | Create | 5 API endpoints |
| `backend/main.py` | Modify | Register new router |
| `backend/tests/test_manual_intel.py` | Create | Storage + endpoint tests |
| `frontend/src/components/Sidebar.jsx` | Modify | Add menu entry |
| `frontend/src/App.jsx` | Modify | Add `/manual-intel` route |
| `frontend/src/pages/ManualIntelPage.jsx` | Create | Full page component |

---

## Task 1: Storage Layer

**Files:**
- Modify: `backend/services/storage.py` (append to end of file)
- Create: `backend/tests/test_manual_intel.py`

- [ ] **Step 1: Write failing tests for storage functions**

Create `backend/tests/test_manual_intel.py`:

```python
import json
import tempfile
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch, tmp_path):
    """Redirect MANUAL_INTEL_DIR to a temp directory for each test."""
    import services.storage as s
    new_dir = tmp_path / "manual_intel"
    new_dir.mkdir()
    monkeypatch.setattr(s, "MANUAL_INTEL_DIR", new_dir)
    yield new_dir


def test_create_and_get_item():
    from services.storage import create_manual_intel_item, get_manual_intel_item_by_id
    item = create_manual_intel_item({
        "url": "https://example.com/post",
        "title": "Test Article",
        "source_platform": "Blog",
        "user_note": "interesting",
        "content_snippet": "some content",
    })
    assert item["id"]
    assert item["title"] == "Test Article"
    assert item["source_platform"] == "Blog"
    assert item["user_note"] == "interesting"
    assert item["quick_read"] == ""
    assert item["business_opps"] == []
    assert item["rdev_opps"] == []

    found = get_manual_intel_item_by_id(item["id"])
    assert found is not None
    assert found["id"] == item["id"]


def test_get_items_returns_newest_first():
    from services.storage import create_manual_intel_item, get_manual_intel_items
    a = create_manual_intel_item({"url": "https://a.com", "title": "A"})
    b = create_manual_intel_item({"url": "https://b.com", "title": "B"})
    items = get_manual_intel_items()
    assert items[0]["id"] == b["id"]  # newest first
    assert items[1]["id"] == a["id"]


def test_filter_by_platform():
    from services.storage import create_manual_intel_item, get_manual_intel_items
    create_manual_intel_item({"url": "https://x.com/1", "title": "X post", "source_platform": "X"})
    create_manual_intel_item({"url": "https://reddit.com/r/1", "title": "Reddit post", "source_platform": "Reddit"})
    x_items = get_manual_intel_items(source_platform="X")
    assert len(x_items) == 1
    assert x_items[0]["source_platform"] == "X"


def test_update_item():
    from services.storage import create_manual_intel_item, update_manual_intel_item, get_manual_intel_item_by_id
    item = create_manual_intel_item({"url": "https://example.com", "title": "T"})
    updated = update_manual_intel_item(item["id"], {"quick_read": "summary here"})
    assert updated["quick_read"] == "summary here"
    # Persisted
    found = get_manual_intel_item_by_id(item["id"])
    assert found["quick_read"] == "summary here"


def test_delete_item():
    from services.storage import create_manual_intel_item, delete_manual_intel_item, get_manual_intel_item_by_id
    item = create_manual_intel_item({"url": "https://example.com", "title": "T"})
    ok = delete_manual_intel_item(item["id"])
    assert ok is True
    assert get_manual_intel_item_by_id(item["id"]) is None


def test_delete_nonexistent_returns_false():
    from services.storage import delete_manual_intel_item
    assert delete_manual_intel_item("nonexistent-id") is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
source venv/bin/activate
cd backend
python -m pytest tests/test_manual_intel.py -v
```

Expected: `ImportError` or `AttributeError` — functions not yet defined.

- [ ] **Step 3: Implement storage functions**

Append to the end of `backend/services/storage.py`:

```python
# ───────────────────────── 手动情报 ─────────────────────────

MANUAL_INTEL_DIR = DATA_DIR / "manual_intel"
MANUAL_INTEL_DIR.mkdir(parents=True, exist_ok=True)

_MANUAL_INTEL_FILE = MANUAL_INTEL_DIR / "items.json"


def _load_manual_intel() -> List[Dict]:
    if _MANUAL_INTEL_FILE.exists():
        return json.loads(_MANUAL_INTEL_FILE.read_text(encoding="utf-8"))
    return []


def _save_manual_intel(items: List[Dict]):
    _MANUAL_INTEL_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def get_manual_intel_items(source_platform: Optional[str] = None) -> List[Dict]:
    items = _load_manual_intel()
    if source_platform:
        items = [i for i in items if i.get("source_platform") == source_platform]
    return sorted(items, key=lambda x: x.get("added_at", ""), reverse=True)


def get_manual_intel_item_by_id(item_id: str) -> Optional[Dict]:
    for item in _load_manual_intel():
        if item["id"] == item_id:
            return item
    return None


def create_manual_intel_item(data: Dict) -> Dict:
    items = _load_manual_intel()
    item = {
        "id": str(uuid.uuid4()),
        "url": data.get("url", ""),
        "title": data.get("title", ""),
        "source_platform": data.get("source_platform", "other"),
        "user_note": data.get("user_note", ""),
        "added_at": datetime.now().isoformat(),
        "content_snippet": data.get("content_snippet", ""),
        "quick_read": "",
        "business_opps": [],
        "rdev_opps": [],
    }
    items.append(item)
    _save_manual_intel(items)
    return item


def update_manual_intel_item(item_id: str, updates: Dict) -> Optional[Dict]:
    items = _load_manual_intel()
    for item in items:
        if item["id"] == item_id:
            item.update(updates)
            _save_manual_intel(items)
            return item
    return None


def delete_manual_intel_item(item_id: str) -> bool:
    items = _load_manual_intel()
    new_items = [i for i in items if i["id"] != item_id]
    if len(new_items) == len(items):
        return False
    _save_manual_intel(new_items)
    return True
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_manual_intel.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
git add backend/services/storage.py backend/tests/test_manual_intel.py
git commit -m "feat: add manual_intel storage layer with CRUD functions"
```

---

## Task 2: Read-Only Router Endpoints + Register in main.py

**Files:**
- Create: `backend/routers/manual_intel.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/test_manual_intel.py` (add endpoint tests)

- [ ] **Step 1: Write failing endpoint tests**

Append to `backend/tests/test_manual_intel.py`:

```python
from fastapi.testclient import TestClient


@pytest.fixture
def client(isolated_storage):
    import importlib, sys
    # Re-import app fresh so it picks up the monkeypatched storage dir
    for mod in list(sys.modules.keys()):
        if mod.startswith("routers") or mod.startswith("services"):
            del sys.modules[mod]
    from main import app
    return TestClient(app)


def test_get_items_empty(client):
    resp = client.get("/api/manual-intel")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_get_item_not_found(client):
    resp = client.get("/api/manual-intel/does-not-exist")
    assert resp.status_code == 404


def test_delete_item_not_found(client):
    resp = client.delete("/api/manual-intel/does-not-exist")
    assert resp.status_code == 404


def test_create_and_list_and_delete(client, monkeypatch):
    # Monkeypatch the URL fetch so we don't make real HTTP calls
    async def fake_fetch(url):
        return "Fake Title", "Fake content snippet"

    import routers.manual_intel as mi
    monkeypatch.setattr(mi, "_fetch_url_content", fake_fetch)

    # Also patch the AI analysis so it doesn't run
    monkeypatch.setattr(mi, "_run_ai_analysis", lambda item_id: None)

    resp = client.post("/api/manual-intel", json={
        "url": "https://example.com/article",
        "source_platform": "Blog",
        "user_note": "great read",
    })
    assert resp.status_code == 201
    item = resp.json()
    assert item["title"] == "Fake Title"
    assert item["user_note"] == "great read"
    item_id = item["id"]

    # List
    resp = client.get("/api/manual-intel")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1

    # Get single
    resp = client.get(f"/api/manual-intel/{item_id}")
    assert resp.status_code == 200

    # Delete
    resp = client.delete(f"/api/manual-intel/{item_id}")
    assert resp.status_code == 200

    resp = client.get("/api/manual-intel")
    assert resp.json() == {"items": []}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_manual_intel.py::test_get_items_empty -v
```

Expected: `ImportError` — router not yet created.

- [ ] **Step 3: Create the router with GET list, GET single, DELETE, and a stub POST**

Create `backend/routers/manual_intel.py`:

```python
"""手动情报录入 API"""
import asyncio
import re
from typing import Optional
from fastapi import APIRouter, HTTPException

from services.storage import (
    get_manual_intel_items,
    get_manual_intel_item_by_id,
    create_manual_intel_item,
    update_manual_intel_item,
    delete_manual_intel_item,
)
from services.llm_client import chat_async

router = APIRouter()


async def _fetch_url_content(url: str) -> tuple[str, str]:
    """Fetch a URL and return (title, content_snippet). Never raises — returns empty strings on failure."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 TokenBurner/1.0"}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return "", ""
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title else ""
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            snippet = soup.get_text(separator=" ", strip=True)[:6000]
            return title, snippet
    except Exception as e:
        print(f"[manual-intel] fetch failed for {url}: {e}")
        return "", ""


async def _run_ai_analysis(item_id: str):
    """Run quick_read, business_opps, rdev_opps in sequence and persist each result."""
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        return

    title = item.get("title", "")
    snippet = item.get("content_snippet", "")

    # ── Quick read ──────────────────────────────────────────
    quick_read_prompt = f"""请对以下文章进行速读总结，帮助读者快速了解核心内容。

文章标题：{title}
原文内容（节选）：
{snippet}

请用中文输出，严格使用以下 Markdown 格式：
**核心内容**：用 2-3 句话说清楚文章讲了什么（面向技术/创业读者）

**关键信息**：
- 要点一
- 要点二
- 要点三（共 3-5 条，每条以 - 开头）

**值得关注**：这篇文章最有价值的一个洞察或信息（1 句话）

直接输出内容，不要重复标题。"""

    try:
        quick_read = (await chat_async([{"role": "user", "content": quick_read_prompt}])).strip()
        update_manual_intel_item(item_id, {"quick_read": quick_read})
    except Exception as e:
        print(f"[manual-intel] quick_read failed for {item_id}: {e}")

    # ── Business opportunities ──────────────────────────────
    biz_prompt = f"""你是一位经验丰富的 AI 产品经理和连续创业者，擅长从技术内容中发现真实可落地的商业机会。

# 开发者背景
- 独立开发者，无团队
- 技术栈：Python / Next.js
- 可接受面向全球或中文市场的产品

# 文章信息
标题：{title}
内容节选：{snippet[:3000]}

# 任务
基于以上文章，识别 1-3 个可落地的商业机会。如果文章内容无商业机会（纯商业新闻、人事变动等），返回空数组 []。

# 输出格式（严格 JSON，不要 markdown 代码块）
[
  {{
    "opportunity_title": "产品方向名称（30字以内）",
    "core_insight": "这个技术能力如何支撑此产品，之前为何不可行（60字以内）",
    "product_form": "帮助[目标用户]解决[具体问题]的[产品类型]",
    "target_users": "用户画像：职业/场景/痛点/付费意愿（40字以内）",
    "mvp_features": ["核心功能1", "核心功能2", "核心功能3"],
    "business_model": "盈利方式及定价（30字以内）",
    "risks": "最大风险（40字以内）",
    "scores": {{
      "pain_point": 4,
      "market_size": 3,
      "tech_timing": 5,
      "buildability": 4
    }},
    "total_score": 16
  }}
]"""

    try:
        import json as _json
        raw = (await chat_async([{"role": "user", "content": biz_prompt}], provider="deepseek")).strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        business_opps = _json.loads(match.group(0) if match else raw)
        if not isinstance(business_opps, list):
            business_opps = []
        update_manual_intel_item(item_id, {"business_opps": business_opps})
    except Exception as e:
        print(f"[manual-intel] business_opps failed for {item_id}: {e}")
        update_manual_intel_item(item_id, {"business_opps": []})

    # ── R&D opportunities ───────────────────────────────────
    rdev_prompt = f"""你是一位深度嵌入顶级互联网大厂的 AI 架构师兼技术顾问，深知研发团队的真实痛点。

# 文章信息
标题：{title}
内容节选：{snippet[:3000]}

# 任务
基于以上文章，挖掘 1-3 个可落地的研发提效或业务赋能机会。如文章无技术内容，返回空数组 []。

# 输出格式（严格 JSON，不要 markdown 代码块）
[
  {{
    "type": "研发提效",
    "title": "一句话方案名称（20字以内）",
    "trigger": "哪个技术点触发了这个机会（30字以内）",
    "scenario": "在[具体场景]中，目前做法是[现有做法]，核心痛点在于[问题所在]（80字以内）",
    "ai_solution": "新技术如何重构这个场景（80字以内）",
    "implementation": "具体集成形态，如VS Code插件/GitLab Webhook等（60字以内）",
    "audience": ["大前端", "客户端"],
    "impact": "量化预期收益（50字以内）",
    "difficulty": "低",
    "scores": {{
      "efficiency": 8,
      "feasibility": 7,
      "business_impact": 6,
      "overall": 8
    }},
    "total_score": 8
  }}
]

type 只能是"研发提效"或"业务赋能"。difficulty 只能是"低"、"中"、"高"。"""

    try:
        import json as _json
        raw = (await chat_async([{"role": "user", "content": rdev_prompt}], provider="deepseek")).strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        rdev_opps = _json.loads(match.group(0) if match else raw)
        if not isinstance(rdev_opps, list):
            rdev_opps = []
        update_manual_intel_item(item_id, {"rdev_opps": rdev_opps})
    except Exception as e:
        print(f"[manual-intel] rdev_opps failed for {item_id}: {e}")
        update_manual_intel_item(item_id, {"rdev_opps": []})


@router.get("")
async def list_items(source_platform: Optional[str] = None):
    items = get_manual_intel_items(source_platform=source_platform)
    return {"items": items}


@router.get("/{item_id}")
async def get_item(item_id: str):
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("", status_code=201)
async def create_item(body: dict):
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url required")

    title, content_snippet = await _fetch_url_content(url)
    if not title:
        title = url  # fallback: use URL as title if fetch failed

    item = create_manual_intel_item({
        "url": url,
        "title": title,
        "source_platform": body.get("source_platform", "other"),
        "user_note": body.get("user_note", ""),
        "content_snippet": content_snippet,
    })

    asyncio.create_task(_run_ai_analysis(item["id"]))
    return item


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    ok = delete_manual_intel_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.post("/{item_id}/reanalyze")
async def reanalyze_item(item_id: str):
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    update_manual_intel_item(item_id, {"quick_read": "", "business_opps": [], "rdev_opps": []})
    asyncio.create_task(_run_ai_analysis(item_id))
    return {"ok": True, "message": "Re-analysis started"}
```

- [ ] **Step 4: Register the router in main.py**

In `backend/main.py`, after the existing router imports, add:

```python
from routers.manual_intel import router as manual_intel_router
```

And in the router registration block (after the `share_pages_router` line):

```python
app.include_router(manual_intel_router, prefix="/api/manual-intel", tags=["manual-intel"])
```

- [ ] **Step 5: Run all tests to confirm they pass**

```bash
python -m pytest tests/test_manual_intel.py -v
```

Expected: All tests PASS. (The `_run_ai_analysis` is monkeypatched in the endpoint test so no real LLM calls are made.)

- [ ] **Step 6: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
git add backend/routers/manual_intel.py backend/main.py backend/tests/test_manual_intel.py
git commit -m "feat: add manual_intel router with CRUD endpoints and AI analysis"
```

---

## Task 3: Frontend Sidebar + Route

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add sidebar menu entry**

In `frontend/src/components/Sidebar.jsx`, after the "实验想法池" `<Link>` and before the closing `</div>` of the Menu block, add:

```jsx
<div style={{ height: '1px', background: 'var(--border)', margin: '6px 8px' }} />
<Link to="/manual-intel" className={`menu-item ${isActive('/manual-intel') ? 'active' : ''}`}>
  <span>📌</span><span>我的情报收藏</span>
</Link>
```

- [ ] **Step 2: Add route in App.jsx**

In `frontend/src/App.jsx`, add the import:

```jsx
import ManualIntelPage from './pages/ManualIntelPage'
```

And inside `<Routes>`, before `<Route path="*" ...>`:

```jsx
<Route path="/manual-intel" element={<ManualIntelPage />} />
```

- [ ] **Step 3: Create a minimal placeholder page so the route works**

Create `frontend/src/pages/ManualIntelPage.jsx` with:

```jsx
export default function ManualIntelPage() {
  return <div style={{ padding: 32 }}>我的情报收藏 — coming soon</div>
}
```

- [ ] **Step 4: Start dev server and verify**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge/frontend
pnpm dev
```

Open http://localhost:5174, verify:
- Sidebar shows "📌 我的情报收藏" below 实验想法池 with a separator line
- Clicking it navigates to `/manual-intel` and shows the placeholder text
- Active state highlights correctly

- [ ] **Step 5: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
git add frontend/src/components/Sidebar.jsx frontend/src/App.jsx frontend/src/pages/ManualIntelPage.jsx
git commit -m "feat: add manual-intel sidebar entry and route"
```

---

## Task 4: Frontend Page — Full Implementation

**Files:**
- Modify: `frontend/src/pages/ManualIntelPage.jsx` (replace placeholder)

- [ ] **Step 1: Implement ManualIntelPage.jsx**

Replace the entire contents of `frontend/src/pages/ManualIntelPage.jsx`:

```jsx
import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'

const PLATFORMS = ['X', 'Reddit', 'Blog', 'HackerNews', 'other']

const PLATFORM_BADGES = {
  X:          { label: '𝕏',          style: { background: '#f0f0f0', color: '#333' } },
  Reddit:     { label: 'Reddit',     style: { background: '#fff0eb', color: '#c0392b' } },
  Blog:       { label: 'Blog',       style: { background: '#eef2ff', color: '#4338ca' } },
  HackerNews: { label: 'HN',         style: { background: '#fff7ed', color: '#c2410c' } },
  other:      { label: '其他',        style: { background: '#f3f4f6', color: '#6b7280' } },
}

function Badge({ platform }) {
  const cfg = PLATFORM_BADGES[platform] || PLATFORM_BADGES.other
  return (
    <span style={{
      fontSize: 11, padding: '2px 7px', borderRadius: 4, fontWeight: 500, ...cfg.style
    }}>{cfg.label}</span>
  )
}

function CollapsibleSection({ icon, title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 7, overflow: 'hidden' }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '8px 12px', background: 'var(--bg-secondary)', cursor: 'pointer',
          fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)',
        }}
      >
        <span>{icon} {title}</span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ padding: '10px 12px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          {children}
        </div>
      )}
    </div>
  )
}

function OpportunityCard({ opp }) {
  return (
    <div style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{opp.opportunity_title}</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>{opp.core_insight}</div>
      <div style={{ fontSize: 12 }}><strong>产品形态：</strong>{opp.product_form}</div>
      <div style={{ fontSize: 12 }}><strong>目标用户：</strong>{opp.target_users}</div>
      {opp.mvp_features?.length > 0 && (
        <div style={{ fontSize: 12, marginTop: 4 }}>
          <strong>MVP 功能：</strong>{opp.mvp_features.join(' · ')}
        </div>
      )}
      <div style={{ fontSize: 12 }}><strong>商业模式：</strong>{opp.business_model}</div>
      <div style={{ fontSize: 12, color: '#dc2626' }}><strong>风险：</strong>{opp.risks}</div>
    </div>
  )
}

function RdevCard({ sol }) {
  return (
    <div style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 11, padding: '2px 6px', borderRadius: 4, background: '#f0fdf4', color: '#15803d' }}>
          {sol.type}
        </span>
        <span style={{ fontWeight: 600, fontSize: 13 }}>{sol.title}</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>难度：{sol.difficulty}</span>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 2 }}>{sol.scenario}</div>
      <div style={{ fontSize: 12 }}><strong>方案：</strong>{sol.ai_solution}</div>
      <div style={{ fontSize: 12 }}><strong>落地形态：</strong>{sol.implementation}</div>
      <div style={{ fontSize: 12, color: '#2563eb' }}><strong>预期收益：</strong>{sol.impact}</div>
    </div>
  )
}

function ItemCard({ item, onDelete, onReanalyze }) {
  const isAnalyzing = !item.quick_read && !item.business_opps?.length && !item.rdev_opps?.length

  return (
    <div style={{
      background: 'var(--bg-primary)', borderRadius: 10, border: '1px solid var(--border)',
      padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <a
            href={item.url} target="_blank" rel="noreferrer"
            style={{ fontSize: 14, fontWeight: 600, color: 'var(--accent)', textDecoration: 'none', lineHeight: 1.4 }}
          >
            {item.title || item.url}
          </a>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            <Badge platform={item.source_platform} />
            <span style={{
              fontSize: 10, padding: '2px 6px', borderRadius: 4, border: '1px solid #bbf7d0',
              background: '#f0fdf4', color: '#15803d',
            }}>手动录入</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {new Date(item.added_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, marginLeft: 12 }}>
          <button
            onClick={() => onReanalyze(item.id)}
            style={{ fontSize: 11, padding: '4px 8px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer', color: 'var(--text-secondary)' }}
          >重新分析</button>
          <button
            onClick={() => onDelete(item.id)}
            style={{ fontSize: 11, padding: '4px 8px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer', color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#fca5a5'; e.currentTarget.style.color = '#dc2626' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
          >删除</button>
        </div>
      </div>

      {/* User note */}
      {item.user_note && (
        <div style={{
          fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-secondary)',
          borderRadius: 5, padding: '6px 10px', marginBottom: 10, fontStyle: 'italic',
        }}>
          💬 {item.user_note}
        </div>
      )}

      {/* Analysis sections */}
      {isAnalyzing ? (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 0' }}>⏳ AI 分析中，请稍候…</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <CollapsibleSection icon="⚡" title="速读摘要" defaultOpen={true}>
            {item.quick_read
              ? <ReactMarkdown>{item.quick_read}</ReactMarkdown>
              : <span style={{ color: 'var(--text-muted)' }}>暂无速读</span>}
          </CollapsibleSection>

          <CollapsibleSection icon="💼" title={`商业机会${item.business_opps?.length ? ` (${item.business_opps.length})` : ''}`}>
            {item.business_opps?.length
              ? item.business_opps.map((opp, i) => <OpportunityCard key={i} opp={opp} />)
              : <span style={{ color: 'var(--text-muted)' }}>未发现明显商业机会</span>}
          </CollapsibleSection>

          <CollapsibleSection icon="🔬" title={`研发机会${item.rdev_opps?.length ? ` (${item.rdev_opps.length})` : ''}`}>
            {item.rdev_opps?.length
              ? item.rdev_opps.map((sol, i) => <RdevCard key={i} sol={sol} />)
              : <span style={{ color: 'var(--text-muted)' }}>未发现研发落地机会</span>}
          </CollapsibleSection>
        </div>
      )}
    </div>
  )
}

export default function ManualIntelPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [platformFilter, setPlatformFilter] = useState('all')
  const [url, setUrl] = useState('')
  const [platform, setPlatform] = useState('other')
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const pollingRef = useRef({}) // { [item_id]: intervalId }

  const fetchItems = useCallback(async () => {
    try {
      const resp = await fetch('/api/manual-intel')
      const data = await resp.json()
      setItems(data.items || [])
    } catch (e) {
      console.error('Failed to fetch manual intel items', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchItems()
    return () => {
      // Clear all polling on unmount
      Object.values(pollingRef.current).forEach(clearInterval)
    }
  }, [fetchItems])

  // Start polling for a newly created item until all three AI fields are populated
  const startPolling = useCallback((itemId) => {
    if (pollingRef.current[itemId]) return
    pollingRef.current[itemId] = setInterval(async () => {
      try {
        const resp = await fetch(`/api/manual-intel/${itemId}`)
        if (!resp.ok) return
        const updated = await resp.json()
        const done = updated.quick_read && updated.business_opps !== undefined && updated.rdev_opps !== undefined &&
                     (updated.quick_read !== '' || updated.business_opps.length > 0 || updated.rdev_opps.length > 0)
        setItems(prev => prev.map(i => i.id === itemId ? updated : i))
        if (done) {
          clearInterval(pollingRef.current[itemId])
          delete pollingRef.current[itemId]
        }
      } catch (e) {
        // ignore, keep polling
      }
    }, 3000)
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return
    setSubmitting(true)
    setSubmitError('')
    try {
      const resp = await fetch('/api/manual-intel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim(), source_platform: platform, user_note: note.trim() }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        setSubmitError(err.detail || '录入失败')
        return
      }
      const newItem = await resp.json()
      setItems(prev => [newItem, ...prev])
      startPolling(newItem.id)
      setUrl('')
      setNote('')
      setPlatform('other')
    } catch (e) {
      setSubmitError('网络错误，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(itemId) {
    await fetch(`/api/manual-intel/${itemId}`, { method: 'DELETE' })
    if (pollingRef.current[itemId]) {
      clearInterval(pollingRef.current[itemId])
      delete pollingRef.current[itemId]
    }
    setItems(prev => prev.filter(i => i.id !== itemId))
  }

  async function handleReanalyze(itemId) {
    await fetch(`/api/manual-intel/${itemId}/reanalyze`, { method: 'POST' })
    setItems(prev => prev.map(i => i.id === itemId
      ? { ...i, quick_read: '', business_opps: [], rdev_opps: [] }
      : i
    ))
    startPolling(itemId)
  }

  const filtered = platformFilter === 'all'
    ? items
    : items.filter(i => i.source_platform === platformFilter)

  const usedPlatforms = [...new Set(items.map(i => i.source_platform).filter(Boolean))]

  return (
    <div>
      {/* Page header */}
      <div style={{ padding: '20px 28px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg-primary)' }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
          📌 我的情报收藏
          <span style={{ fontSize: 12, background: 'var(--bg-secondary)', color: 'var(--text-muted)', borderRadius: 10, padding: '2px 8px' }}>
            {items.length}
          </span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>手动录入的情报，自动生成速读与机会分析</p>
      </div>

      {/* Input form */}
      <div style={{ margin: '16px 28px', background: 'var(--bg-primary)', borderRadius: 10, border: '1px solid var(--border)', padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <input
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="粘贴文章链接…"
              required
              style={{
                flex: 1, border: '1.5px solid var(--border)', borderRadius: 6,
                padding: '9px 12px', fontSize: 13, color: 'var(--text-primary)',
                background: 'var(--bg-secondary)', outline: 'none',
              }}
            />
            <select
              value={platform}
              onChange={e => setPlatform(e.target.value)}
              style={{
                border: '1.5px solid var(--border)', borderRadius: 6,
                padding: '9px 10px', fontSize: 13, background: 'var(--bg-secondary)',
                color: 'var(--text-primary)', width: 130,
              }}
            >
              {PLATFORMS.map(p => (
                <option key={p} value={p}>{p === 'X' ? '𝕏 (Twitter)' : p}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={submitting}
              style={{
                background: submitting ? '#93c5fd' : '#1a56db', color: '#fff',
                border: 'none', borderRadius: 6, padding: '9px 16px',
                fontSize: 13, fontWeight: 500, cursor: submitting ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
              }}
            >
              {submitting ? '录入中…' : '+ 录入情报'}
            </button>
          </div>
          <textarea
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="添加点评（可选）：为什么觉得这条内容值得收藏？"
            rows={2}
            style={{
              width: '100%', border: '1.5px solid var(--border)', borderRadius: 6,
              padding: '8px 12px', fontSize: 12, color: 'var(--text-secondary)',
              background: 'var(--bg-secondary)', resize: 'none', fontFamily: 'inherit',
            }}
          />
          {submitError && <p style={{ fontSize: 12, color: '#dc2626', marginTop: 6 }}>{submitError}</p>}
        </form>
      </div>

      {/* Platform filter chips */}
      {usedPlatforms.length > 1 && (
        <div style={{ display: 'flex', gap: 6, padding: '0 28px 12px', flexWrap: 'wrap' }}>
          {['all', ...usedPlatforms].map(p => (
            <button
              key={p}
              onClick={() => setPlatformFilter(p)}
              style={{
                fontSize: 12, padding: '4px 12px', borderRadius: 20,
                border: '1px solid var(--border)', cursor: 'pointer',
                background: platformFilter === p ? '#1a56db' : 'var(--bg-primary)',
                color: platformFilter === p ? '#fff' : 'var(--text-secondary)',
                borderColor: platformFilter === p ? '#1a56db' : 'var(--border)',
              }}
            >
              {p === 'all' ? '全部' : p}
            </button>
          ))}
        </div>
      )}

      {/* Items list */}
      <div style={{ padding: '0 28px 28px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)', fontSize: 14 }}>加载中…</div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)', fontSize: 14 }}>
            还没有情报，粘贴一个链接试试 👆
          </div>
        ) : (
          filtered.map(item => (
            <ItemCard
              key={item.id}
              item={item}
              onDelete={handleDelete}
              onReanalyze={handleReanalyze}
            />
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Start the full stack and test the golden path**

Terminal 1 — backend:
```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge/backend
source ../venv/bin/activate
uvicorn main:app --port 8001 --reload
```

Terminal 2 — frontend:
```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge/frontend
pnpm dev
```

Open http://localhost:5174/manual-intel and verify:
1. Page loads with input form and empty state message
2. Paste a real URL (e.g. a blog post), select platform, optionally add a note, click "录入情报"
3. New card appears immediately with "⏳ AI 分析中" message
4. After ~30–60 seconds (AI runs), card updates with 速读摘要 / 商业机会 / 研发机会
5. Collapsible sections expand and collapse correctly
6. Filter chips appear when multiple platforms are present
7. Delete removes the card
8. "重新分析" resets the card to loading state and re-runs AI

- [ ] **Step 3: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
git add frontend/src/pages/ManualIntelPage.jsx
git commit -m "feat: implement ManualIntelPage with URL input, item cards, and AI analysis polling"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Sidebar entry below 实验想法池 with separator — Task 3 Step 1
- ✅ Paste URL → auto-fetch title + content — Task 2 Step 3 (`_fetch_url_content`)
- ✅ Optional user note / 点评 — POST body `user_note`, displayed in card
- ✅ Source platform tag — Task 2 Step 3 + Task 4 `Badge` component
- ✅ "手动录入" badge distinct from auto-collected — Task 4 card header
- ✅ Immediate AI analysis on create — `asyncio.create_task(_run_ai_analysis(...))` in POST
- ✅ Speed read, business opps, rdev opps — Task 2 Step 3 `_run_ai_analysis`
- ✅ Independent page (not mixed with daily briefing) — separate route `/manual-intel`
- ✅ Data stored in `data/manual_intel/` — Task 1 storage layer
- ✅ Delete item — DELETE endpoint + handleDelete in UI
- ✅ Reanalyze — POST `/{id}/reanalyze` endpoint + handleReanalyze in UI
- ✅ Polling until AI done — `startPolling` function with 3s interval
- ✅ Filter by platform — `usedPlatforms` chips + frontend filter

**Type consistency:**
- `_fetch_url_content` → returns `tuple[str, str]` — used correctly in POST
- `create_manual_intel_item` → keys match storage implementation exactly
- `update_manual_intel_item(item_id, updates)` — consistent across Task 1 and Task 2
- `business_opps` / `rdev_opps` initialized as `[]` in storage, stored as list from AI — consistent

**No placeholders:** All steps contain actual code. No TBDs.
