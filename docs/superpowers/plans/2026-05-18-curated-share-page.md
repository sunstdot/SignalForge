# 精选分享页生成器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AI情报页和全部机会页加多选框，用户挑选内容后点按钮生成精选版分享页，覆盖同日期的 `{date}.html`。

**Architecture:** 新增 `POST /api/share-pages/generate` 接口，接收选中的情报 ID 和机会 ID，过滤后调用现有 `build_share_payload` + `render_share_page_html`，覆盖写入文件。前端用 `useShareSelection(date)` hook（localStorage 持久化）跨页共享选中状态，两个页面的 sticky header 各嵌入操作栏。

**Tech Stack:** FastAPI (Python), React (JSX), localStorage, unittest + FastAPI TestClient

---

## 文件清单

| 文件 | 操作 |
|---|---|
| `backend/routers/share_pages.py` | 新建 — POST endpoint + 两个过滤函数 |
| `backend/tests/test_share_pages_router.py` | 新建 — 过滤逻辑 + endpoint 集成测试 |
| `backend/main.py` | 修改 — 在 StaticFiles mount 之前注册新路由 |
| `frontend/src/pages/useShareSelection.js` | 新建 — hook + ShareSelectionBar 组件 |
| `frontend/src/pages/BriefingPage.jsx` | 修改 — 加 hook、操作栏、ContentCard 复选框 |
| `frontend/src/pages/OpportunityDashboard.jsx` | 修改 — 加 rawId、hook、操作栏、OpportunityCard 复选框 |

---

### Task 1: 后端路由 — share_pages.py

**Files:**
- Create: `backend/routers/share_pages.py`
- Create: `backend/tests/test_share_pages_router.py`

- [ ] **Step 1: 新建路由文件**

`backend/routers/share_pages.py`:

```python
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.share_page import (
    _load_share_sources,
    build_share_payload,
    render_share_page_html,
)

router = APIRouter()

SHARE_PAGES_DIR = Path(__file__).parent.parent / "docs" / "share-pages"


class GenerateRequest(BaseModel):
    date: str
    signal_ids: List[str]
    opportunity_ids: List[str]


def _filter_opportunities(opportunities: list, opportunity_ids: List[str]) -> list:
    id_set = set(opportunity_ids)
    return [
        item for item in opportunities
        if str(item.get("item_id", "")) in id_set
        or item.get("opportunity_title", "") in id_set
    ]


def _filter_content_items(content_items: list, signal_ids: List[str]) -> list:
    id_set = set(signal_ids)
    return [item for item in content_items if item.get("id") in id_set]


@router.post("/generate")
async def generate_share_page(req: GenerateRequest):
    try:
        opportunities, content_items, quick_reads = _load_share_sources(req.date)

        filtered_opps = _filter_opportunities(opportunities, req.opportunity_ids)
        filtered_items = _filter_content_items(content_items, req.signal_ids)

        payload = build_share_payload(
            req.date, filtered_opps, filtered_items, quick_reads,
            opportunity_limit=99, briefing_limit=99,
        )
        html = render_share_page_html(payload)

        SHARE_PAGES_DIR.mkdir(parents=True, exist_ok=True)
        output_path = SHARE_PAGES_DIR / f"{req.date}.html"
        output_path.write_text(html, encoding="utf-8")

        return {"url": f"/api/share-pages/{req.date}.html"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: 写失败测试**

`backend/tests/test_share_pages_router.py`:

```python
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from routers.share_pages import _filter_opportunities, _filter_content_items

_SAMPLE_OPP_1 = {
    "item_id": "o1", "opportunity_title": "Opp One", "total_score": 18,
    "core_insight": "ci", "product_form": "pf", "business_model": "bm",
    "target_users": "tu", "mvp_features": [], "risks": "r",
}
_SAMPLE_OPP_2 = {
    "item_id": "o2", "opportunity_title": "Opp Two", "total_score": 15,
    "core_insight": "ci2", "product_form": "pf2", "business_model": "bm2",
    "target_users": "tu2", "mvp_features": [], "risks": "r2",
}
_SAMPLE_ITEM_1 = {"id": "s1", "title": "Signal One", "source": "GitHub", "source_type": "repo", "relevance_score": 9}
_SAMPLE_ITEM_2 = {"id": "s2", "title": "Signal Two", "source": "arXiv", "source_type": "paper", "relevance_score": 8}
_QUICK_READS = {"s1": "quick read one", "s2": "quick read two"}


class TestFilterOpportunities(unittest.TestCase):
    def test_match_by_item_id(self):
        result = _filter_opportunities([_SAMPLE_OPP_1, _SAMPLE_OPP_2], ["o1"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["item_id"], "o1")

    def test_match_by_title_when_no_item_id(self):
        opps = [{"opportunity_title": "Opp A"}, {"opportunity_title": "Opp B"}]
        result = _filter_opportunities(opps, ["Opp A"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["opportunity_title"], "Opp A")

    def test_empty_ids_returns_empty(self):
        self.assertEqual(_filter_opportunities([_SAMPLE_OPP_1], []), [])

    def test_multiple_ids(self):
        result = _filter_opportunities([_SAMPLE_OPP_1, _SAMPLE_OPP_2], ["o1", "o2"])
        self.assertEqual(len(result), 2)


class TestFilterContentItems(unittest.TestCase):
    def test_match_by_id(self):
        result = _filter_content_items([_SAMPLE_ITEM_1, _SAMPLE_ITEM_2], ["s1"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "s1")

    def test_empty_ids_returns_empty(self):
        self.assertEqual(_filter_content_items([_SAMPLE_ITEM_1], []), [])


class TestGenerateEndpoint(unittest.TestCase):
    def setUp(self):
        from main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def test_returns_url_and_writes_html(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("routers.share_pages._load_share_sources",
                       return_value=([_SAMPLE_OPP_1, _SAMPLE_OPP_2], [_SAMPLE_ITEM_1, _SAMPLE_ITEM_2], _QUICK_READS)):
                with patch("routers.share_pages.SHARE_PAGES_DIR", tmp_path):
                    resp = self.client.post("/api/share-pages/generate", json={
                        "date": "2026-05-18",
                        "signal_ids": ["s1"],
                        "opportunity_ids": ["o1"],
                    })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["url"], "/api/share-pages/2026-05-18.html")
        html = (tmp_path / "2026-05-18.html").read_text()
        self.assertIn("Opp One", html)
        self.assertNotIn("Opp Two", html)
        self.assertIn("Signal One", html)
        self.assertNotIn("Signal Two", html)
```

- [ ] **Step 3: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_share_pages_router.py -v 2>&1 | head -30
```

期望：`ModuleNotFoundError` 或类似错误（路由文件已建但 main.py 还没注册）

- [ ] **Step 4: Commit**

```bash
git add backend/routers/share_pages.py backend/tests/test_share_pages_router.py
git commit -m "feat: add share_pages router with filtering functions"
```

---

### Task 2: 在 main.py 注册新路由

**Files:**
- Modify: `backend/main.py:50-60`（在 StaticFiles mount 之前）

- [ ] **Step 1: 修改 main.py**

在 `backend/main.py` 中，找到这一段：

```python
from routers import briefing, dates, experiments, content
from routers.experiments import router as experiments_router
```

改为：

```python
from routers import briefing, dates, experiments, content
from routers.experiments import router as experiments_router
from routers.share_pages import router as share_pages_router
```

然后找到现有路由注册块末尾（`app.include_router(content.router, ...)`之后，`app.mount(...)` 之前），插入：

```python
app.include_router(share_pages_router, prefix="/api/share-pages", tags=["share-pages"])
```

最终顺序：

```python
app.include_router(briefing.router, prefix="/api/briefing", tags=["briefing"])
app.include_router(dates.router, prefix="/api/dates", tags=["dates"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(share_pages_router, prefix="/api/share-pages", tags=["share-pages"])

# 挂载静态分享页目录（必须在路由注册之后）
share_pages_dir = Path(__file__).parent / "docs" / "share-pages"
if share_pages_dir.exists():
    app.mount("/api/share-pages", StaticFiles(directory=str(share_pages_dir)), name="share-pages")
```

- [ ] **Step 2: 运行测试，确认全部通过**

```bash
cd backend && python -m pytest tests/test_share_pages_router.py -v
```

期望：

```
tests/test_share_pages_router.py::TestFilterOpportunities::test_match_by_item_id PASSED
tests/test_share_pages_router.py::TestFilterOpportunities::test_match_by_title_when_no_item_id PASSED
tests/test_share_pages_router.py::TestFilterOpportunities::test_empty_ids_returns_empty PASSED
tests/test_share_pages_router.py::TestFilterOpportunities::test_multiple_ids PASSED
tests/test_share_pages_router.py::TestFilterContentItems::test_match_by_id PASSED
tests/test_share_pages_router.py::TestFilterContentItems::test_empty_ids_returns_empty PASSED
tests/test_share_pages_router.py::TestGenerateEndpoint::test_returns_url_and_writes_html PASSED
```

- [ ] **Step 3: 验证 API 可达（可选，需后端运行中）**

```bash
curl -s -X POST http://localhost:8001/api/share-pages/generate \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-05-17","signal_ids":[],"opportunity_ids":[]}' | python -m json.tool
```

期望：`{"url": "/api/share-pages/2026-05-17.html"}`（即使 IDs 为空也成功，只是生成空内容页）

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: register share_pages router before StaticFiles mount"
```

---

### Task 3: useShareSelection hook + ShareSelectionBar 组件

**Files:**
- Create: `frontend/src/pages/useShareSelection.js`

- [ ] **Step 1: 新建文件**

`frontend/src/pages/useShareSelection.js`:

```js
import { useState, useEffect, useCallback } from 'react'

export function useShareSelection(date) {
  const key = `sf-selection-${date}`

  const [selection, setSelection] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(key)) || { signal_ids: [], opportunity_ids: [] }
    } catch {
      return { signal_ids: [], opportunity_ids: [] }
    }
  })
  const [generating, setGenerating] = useState(false)

  // 当 date 变化时从 localStorage 重新加载
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(key))
      setSelection(stored || { signal_ids: [], opportunity_ids: [] })
    } catch {
      setSelection({ signal_ids: [], opportunity_ids: [] })
    }
  }, [key])

  // 选中状态变化时写入 localStorage
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(selection))
  }, [key, selection])

  const toggleSignal = useCallback((id) => {
    setSelection(s => ({
      ...s,
      signal_ids: s.signal_ids.includes(id)
        ? s.signal_ids.filter(x => x !== id)
        : [...s.signal_ids, id],
    }))
  }, [])

  const toggleOpportunity = useCallback((id) => {
    setSelection(s => ({
      ...s,
      opportunity_ids: s.opportunity_ids.includes(id)
        ? s.opportunity_ids.filter(x => x !== id)
        : [...s.opportunity_ids, id],
    }))
  }, [])

  const clearAll = useCallback(() => {
    setSelection({ signal_ids: [], opportunity_ids: [] })
  }, [])

  const generate = useCallback(async () => {
    setGenerating(true)
    try {
      const res = await fetch('/api/share-pages/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date,
          signal_ids: selection.signal_ids,
          opportunity_ids: selection.opportunity_ids,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      window.open(`/api/share-pages/${date}.html`, '_blank')
    } catch (e) {
      console.error('[generate share page] failed:', e)
    } finally {
      setGenerating(false)
    }
  }, [date, selection])

  return {
    signalIds: selection.signal_ids,
    opportunityIds: selection.opportunity_ids,
    count: selection.signal_ids.length + selection.opportunity_ids.length,
    toggleSignal,
    toggleOpportunity,
    clearAll,
    generating,
    generate,
  }
}

export function ShareSelectionBar({ signalIds, opportunityIds, generating, onClear, onGenerate }) {
  const count = signalIds.length + opportunityIds.length
  if (count === 0) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '6px 0', marginTop: 6, fontSize: 12,
    }}>
      <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
        已选{' '}
        <strong style={{ color: 'var(--text-primary)' }}>{signalIds.length} 条情报</strong>
        {' · '}
        <strong style={{ color: 'var(--text-primary)' }}>{opportunityIds.length} 个机会</strong>
      </span>
      <span style={{ flex: 1 }} />
      <button
        onClick={onClear}
        disabled={generating}
        style={{
          background: 'transparent',
          border: '1px solid var(--border)',
          color: 'var(--text-muted)',
          padding: '3px 10px',
          borderRadius: 5,
          fontSize: 11,
          cursor: 'pointer',
        }}
      >
        清空
      </button>
      <button
        onClick={onGenerate}
        disabled={generating || count === 0}
        style={{
          background: '#9a3412',
          border: 'none',
          color: 'white',
          padding: '3px 12px',
          borderRadius: 5,
          fontSize: 11,
          fontWeight: 600,
          cursor: generating ? 'default' : 'pointer',
          opacity: generating ? 0.6 : 1,
        }}
      >
        {generating ? '生成中...' : '生成分享页 →'}
      </button>
    </div>
  )
}
```

- [ ] **Step 2: 确认文件存在**

```bash
test -f frontend/src/pages/useShareSelection.js && echo "OK" || echo "MISSING"
```

期望：`OK`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/useShareSelection.js
git commit -m "feat: add useShareSelection hook and ShareSelectionBar component"
```

---

### Task 4: BriefingPage — 操作栏 + ContentCard 复选框

**Files:**
- Modify: `frontend/src/pages/BriefingPage.jsx`

- [ ] **Step 1: 在 BriefingPage 顶部引入 hook 和组件**

在 `BriefingPage.jsx` 第 1 行的 import 列表后，添加：

```js
import { useShareSelection, ShareSelectionBar } from './useShareSelection'
```

- [ ] **Step 2: 在 BriefingPage 函数体内调用 hook**

在 `function BriefingPage()` 内，`const { date } = useParams()` 之后，添加：

```js
const { signalIds, opportunityIds, count, toggleSignal, clearAll, generating, generate } = useShareSelection(date)
```

- [ ] **Step 3: 在 header 内加操作栏**

找到 header 内的面包屑 div（结束于 `</div>` 后接 `</header>`）：

```jsx
        <div className="flex items-center gap-4 mb-4">
          ...
        </div>
      </header>
```

在 `</div>` 和 `</header>` 之间插入：

```jsx
        <ShareSelectionBar
          signalIds={signalIds}
          opportunityIds={opportunityIds}
          generating={generating}
          onClear={clearAll}
          onGenerate={generate}
        />
```

- [ ] **Step 4: 给 ContentCard 传 selected 和 onToggle**

找到 `filteredItems.map(...)` 这段（约第 262 行）：

```jsx
          {filteredItems.map((item, index) => (
            <ContentCard key={item.id} item={item} index={index + 1}
              cachedSummary={quickReads[item.id]}
              date={date}
              onQuickRead={(id, summary) => setQuickReads(prev => ({ ...prev, [id]: summary }))}
            />
          ))}
```

改为：

```jsx
          {filteredItems.map((item, index) => (
            <ContentCard key={item.id} item={item} index={index + 1}
              cachedSummary={quickReads[item.id]}
              date={date}
              onQuickRead={(id, summary) => setQuickReads(prev => ({ ...prev, [id]: summary }))}
              selected={signalIds.includes(item.id)}
              onToggle={() => toggleSignal(item.id)}
            />
          ))}
```

- [ ] **Step 5: 在 ContentCard 函数签名中接受新 props 并渲染复选框**

找到 `function ContentCard({ item, index, cachedSummary, date, onQuickRead })` （约第 725 行），改为：

```jsx
function ContentCard({ item, index, cachedSummary, date, onQuickRead, selected = false, onToggle }) {
```

找到 `return (` 后的 `<article className="content-card">` 这行，改为：

```jsx
    <article className="content-card" style={selected ? { outline: '1px solid #2563eb', outlineOffset: '-1px' } : {}}>
```

找到 `<div className="card-header">` 下方的第一个元素（`<span className="text-sm"...>#{index}</span>`），在其前面插入：

```jsx
        <button
          onClick={e => { e.stopPropagation(); if (cachedSummary) onToggle?.() }}
          title={!cachedSummary ? '暂无速读，无法加入分享页' : (selected ? '取消选择' : '加入分享页')}
          style={{
            width: 16, height: 16, borderRadius: 3, flexShrink: 0,
            border: `1.5px solid ${selected ? '#2563eb' : cachedSummary ? '#4b5563' : '#1f2937'}`,
            background: selected ? '#2563eb' : 'transparent',
            color: 'white', fontSize: 9,
            cursor: cachedSummary ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 0,
          }}
        >
          {selected && '✓'}
        </button>
```

- [ ] **Step 6: 启动开发服务器，人工验证**

```bash
cd frontend && npm run dev
```

访问 `http://localhost:5174/briefing/2026-05-17`：
- 每条情报左侧有小方块
- 有速读的条目：点击方块变蓝并显示 ✓，header 出现操作栏
- 无速读的条目：方块灰色，cursor 为 default，点击无效
- 切换到 `/opportunities/2026-05-17` 再回来，选中状态依然存在

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/BriefingPage.jsx
git commit -m "feat: add signal selection bar and checkboxes to BriefingPage"
```

---

### Task 5: OpportunityDashboard — 操作栏 + 商业机会复选框

**Files:**
- Modify: `frontend/src/pages/OpportunityDashboard.jsx`

- [ ] **Step 1: 引入 hook 和组件**

在 `OpportunityDashboard.jsx` 顶部 import 列表末尾添加：

```js
import { useShareSelection, ShareSelectionBar } from './useShareSelection'
```

- [ ] **Step 2: 给 normalizeBusiness 加 rawId 字段**

找到 `function normalizeBusiness(item)` 的 return 对象（约第 26 行），在 `id:` 之后插入：

```js
    rawId: item.item_id || item.opportunity_title,
```

完整 return 对象开头变为：

```js
  return {
    id: `business-${item.item_id || item.opportunity_title}`,
    rawId: item.item_id || item.opportunity_title,
    kind: 'business',
    ...
```

- [ ] **Step 3: 在 OpportunityDashboard 函数体内调用 hook**

在 `function OpportunityDashboard()` 内，`const { date } = useParams()` 之后添加：

```js
  const { signalIds, opportunityIds, count, toggleOpportunity, clearAll, generating, generate } = useShareSelection(date)
```

- [ ] **Step 4: 在 header 内加操作栏**

找到 header 的末尾（`<p className="text-sm" ...>商业机会与研发提效...</p>` 后接 `</header>`），在 `</header>` 前插入：

```jsx
        <ShareSelectionBar
          signalIds={signalIds}
          opportunityIds={opportunityIds}
          generating={generating}
          onClear={clearAll}
          onGenerate={generate}
        />
```

- [ ] **Step 5: 给 OpportunityCard 传 selected 和 onToggle**

找到 `filteredItems.map(...)` 这段（约第 178 行）：

```jsx
            {filteredItems.map(item => (
              <OpportunityCard key={item.id} item={item} onOpen={() => setSelected(item)} />
            ))}
```

改为：

```jsx
            {filteredItems.map(item => (
              <OpportunityCard
                key={item.id}
                item={item}
                onOpen={() => setSelected(item)}
                selected={item.kind === 'business' && opportunityIds.includes(item.rawId)}
                onToggle={item.kind === 'business'
                  ? (e) => { e.stopPropagation(); toggleOpportunity(item.rawId) }
                  : null}
              />
            ))}
```

- [ ] **Step 6: 在 OpportunityCard 接受 props 并渲染复选框**

找到 `function OpportunityCard({ item, onOpen })` （约第 199 行），改为：

```jsx
function OpportunityCard({ item, onOpen, selected = false, onToggle }) {
```

找到 `<article className="opportunity-card" onClick={onOpen}>` 这行，改为：

```jsx
  <article
    className="opportunity-card"
    onClick={onOpen}
    style={selected ? { outline: '1px solid #16a34a', outlineOffset: '-1px' } : {}}
  >
```

找到 `<div className="opportunity-card-top">` 的内部，在第一个子元素前插入：

```jsx
      {onToggle && (
        <button
          onClick={onToggle}
          title={selected ? '取消选择' : '加入分享页'}
          style={{
            width: 16, height: 16, borderRadius: 3, flexShrink: 0,
            border: `1.5px solid ${selected ? '#16a34a' : '#4b5563'}`,
            background: selected ? '#16a34a' : 'transparent',
            color: 'white', fontSize: 9,
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 0,
          }}
        >
          {selected && '✓'}
        </button>
      )}
```

- [ ] **Step 7: 人工验证端到端流程**

确保后端已运行（`cd backend && uvicorn main:app --port 8001 --reload`），然后：

1. 访问 `http://localhost:5174/briefing/2026-05-17`
2. 勾选若干有速读的情报（方块变蓝，header 出现操作栏）
3. 跳转到 `http://localhost:5174/opportunities/2026-05-17`
4. 确认 header 操作栏显示之前选的情报数
5. 勾选若干商业机会（rdev 卡片无复选框）
6. 点「生成分享页 →」
7. 确认新标签页打开 `/api/share-pages/2026-05-17.html`，内容只包含所选情报和机会

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/OpportunityDashboard.jsx
git commit -m "feat: add opportunity selection bar and checkboxes to OpportunityDashboard"
```
