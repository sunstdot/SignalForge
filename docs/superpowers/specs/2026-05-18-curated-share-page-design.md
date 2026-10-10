# 精选分享页生成器 Design Spec
Date: 2026-05-18

## 问题与目标

当前 `share-page` 命令自动选取评分最高的 n 个商业机会和 n 条 AI 情报，用户无法干预内容质量。目标是在 AI情报页和全部机会页加入多选机制，让用户手工挑选内容后一键生成分享页，覆盖原有的 `{date}.html`。

---

## 架构概览

```
BriefingPage           OpportunityDashboard
    │ toggle signal id       │ toggle opportunity id
    └──────────┬─────────────┘
               ▼
      useShareSelection(date)
      localStorage key: sf-selection-{date}
      { signal_ids: string[], opportunity_ids: string[] }
               │
               │ POST /api/share-pages/generate
               │ { date, signal_ids, opportunity_ids }
               ▼
      backend: filter → render → overwrite {date}.html
               │
               ▼
      window.open /api/share-pages/{date}.html
```

---

## Frontend

### 1. `useShareSelection(date)` hook — 新文件

**路径：** `frontend/src/pages/useShareSelection.jsx`

- 读写 `localStorage` key `sf-selection-{date}`
- 初始值：`{ signal_ids: [], opportunity_ids: [] }`
- 暴露：
  - `signalIds: string[]`
  - `opportunityIds: string[]`
  - `toggleSignal(id)` — 已存在则移除，否则追加
  - `toggleOpportunity(id)` — 同上
  - `clearAll()` — 重置为空
  - `count: number` — signal_ids.length + opportunity_ids.length
  - `generating: boolean`、`generate(date)` — 调用后端 API

`generate(date)` 行为：
1. `POST /api/share-pages/generate` with `{ date, signal_ids, opportunity_ids }`
2. 成功后 `window.open('/api/share-pages/{date}.html', '_blank')`
3. 失败时 `console.error`（不阻断 UI）

### 2. `BriefingPage.jsx` 修改

**操作栏：** 在 sticky header 内部（现有面包屑下方）条件渲染：
- 仅当 `count > 0` 时显示
- 内容：`已选 {signalIds.length} 条情报 · {opportunityIds.length} 个机会` + 清空按钮 + 生成分享页按钮

**情报列表复选框：**
- 每条情报 item 左侧加 16×16 复选框
- 仅当 `quickReads[item.id]` 存在时可选（有速读才能进分享页）
- 无速读的条目：复选框禁用 + 显示 "暂无速读" 提示
- 选中状态：`signalIds.includes(item.id)`
- 点击整行或复选框均触发 `toggleSignal(item.id)`

### 3. `OpportunityDashboard.jsx` 修改

**操作栏：** 与 BriefingPage 相同结构，嵌入 sticky header。

**机会卡片复选框：**
- 仅 **business 类机会** 支持勾选（分享页模板只渲染业务机会字段；rdev 字段结构不同，本期不支持）
- 在 `normalizeBusiness` 增加 `rawId` 字段：`item.item_id || item.opportunity_title`
- business 类 `OpportunityCard` 左上角加复选框；rdev 卡片不加复选框
- 选中状态：`opportunityIds.includes(item.rawId)`
- 点击复选框触发 `toggleOpportunity(item.rawId)`（阻止冒泡，不触发卡片详情弹窗）

---

## Backend

### 新路由 `routers/share_pages.py`

```
POST /api/share-pages/generate
Body: { date: str, signal_ids: list[str], opportunity_ids: list[str] }
Response 200: { url: str }
Response 422: 参数校验失败
Response 500: 生成失败
```

实现步骤：
1. 调用 `_load_share_sources(date)` 加载全量数据
2. 按 `opportunity_ids` 过滤 opportunities：
   - 匹配 `str(item.get("item_id", ""))` 或 `item.get("opportunity_title", "")`
3. 按 `signal_ids` 过滤 content_items：
   - 匹配 `item.get("id")`
4. 调用 `build_share_payload(date, filtered_opps, filtered_items, quick_reads, opportunity_limit=99, briefing_limit=99)`（不再自动截断）
5. 调用 `render_share_page_html(payload)` 生成 HTML
6. 覆盖写入 `docs/share-pages/{date}.html`
7. 返回 `{ "url": f"/api/share-pages/{date}.html" }`

### `main.py` 修改

注册新路由：
```python
from routers.share_pages import router as share_pages_router
app.include_router(share_pages_router, prefix="/api/share-pages", tags=["share-pages"])
```

注意：StaticFiles mount 在 `/api/share-pages` 已存在，新路由需在 StaticFiles mount **之前** 注册，FastAPI 路由优先级高于 StaticFiles。

---

## 数据流：opportunity_id 对齐（仅 business 机会）

| 层 | 值 |
|---|---|
| 后端 JSON（`opportunities/{date}.json`） | `item_id: "abc123"` 或 `opportunity_title: "AI驱动..."` |
| `normalizeBusiness` rawId | `item.item_id \|\| item.opportunity_title` |
| localStorage | `rawId` 字符串 |
| POST body `opportunity_ids` | `[rawId, ...]` |
| 后端过滤 | `str(item.get("item_id","")) in id_set or item.get("opportunity_title","") in id_set` |

> 研发机会（rdev）当前不出现在分享页，本期 OpportunityDashboard 的 rdev 卡片不加复选框。

---

## 边界情况

- **空选择：** 按钮禁用（`count === 0`），不发请求
- **无速读情报：** 禁用复选框，显示提示，后端不会收到该 ID
- **日期切换：** `useShareSelection` 随 `date` 变化重新从 localStorage 读取对应 key，选择不互相干扰
- **覆盖：** 生成后直接覆盖同名文件，原有自动生成版本不保留（符合用户预期）
- **并发：** 生成中按钮禁用，防止重复提交

---

## 改动文件清单

| 文件 | 操作 |
|---|---|
| `frontend/src/pages/useShareSelection.jsx` | 新建 |
| `frontend/src/pages/BriefingPage.jsx` | 修改：加 hook、操作栏、复选框 |
| `frontend/src/pages/OpportunityDashboard.jsx` | 修改：加 hook、操作栏、复选框、rawId |
| `backend/routers/share_pages.py` | 新建 |
| `backend/main.py` | 修改：注册新路由（需在 StaticFiles 前） |
