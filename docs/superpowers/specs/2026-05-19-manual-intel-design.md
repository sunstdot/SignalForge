# 手动情报录入功能设计文档

**日期**: 2026-05-19  
**状态**: 待实现

---

## 背景与目标

用户在日常浏览 X、Reddit、博客等平台时会发现高质量内容，需要一个入口将这些内容手动录入到 SignalForge 情报系统中，与自动抓取的情报并列管理，并享有同等的 AI 分析能力（速读、商业机会、研发机会分析）。

---

## 核心设计决策

- **录入方式**：粘贴 URL，系统自动抓取标题和正文节选
- **展示方式**：独立页面，不混入每日 AI 情报
- **AI 分析时机**：录入后立即自动触发，异步执行，不阻塞录入响应
- **架构方案**：独立存储 + 复用现有 AI 服务（方案 C）

---

## 数据模型

存储位置：`data/manual_intel/items.json`（单文件，列表）

```json
{
  "id": "uuid-v4",
  "url": "https://...",
  "title": "文章标题（自动从 URL 抓取）",
  "source_platform": "X | Reddit | Blog | HackerNews | other",
  "user_note": "用户备注（可选，空字符串表示无）",
  "added_at": "2026-05-19T10:00:00",
  "content_snippet": "正文节选（录入时抓取并缓存，前 6000 字符，用于后续 AI 分析）",
  "quick_read": "速读摘要（AI 生成后缓存，初始为空字符串）",
  "business_opps": {},
  "rdev_opps": {}
}
```

**说明**：
- `content_snippet` 在录入时一次性抓取并缓存，后续 AI 分析直接使用，不重复请求 URL
- `quick_read`、`business_opps`、`rdev_opps` 初始为空，异步 AI 分析完成后写入
- `source_platform` 用于前端筛选过滤

---

## 后端架构

### 新增文件

**`backend/routers/manual_intel.py`**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/manual-intel` | GET | 列表，支持 `?source_platform=X` 筛选 |
| `/api/manual-intel` | POST | 录入新条目（见下方流程） |
| `/api/manual-intel/{id}` | GET | 单条详情 |
| `/api/manual-intel/{id}` | DELETE | 删除 |
| `/api/manual-intel/{id}/reanalyze` | POST | 重新触发 AI 分析 |

**POST 录入流程**：
1. 接收 `{ url, source_platform, user_note }`
2. 用 `httpx` + `BeautifulSoup` 抓取 URL，提取标题和正文（复用 `content.py` 中现有的抓取逻辑）
3. 生成 UUID，写入 `data/manual_intel/items.json`
4. 立即返回 `201` 响应（含新条目 id）
5. 后台异步触发三项 AI 分析（`asyncio.create_task`）：速读、商业机会、研发机会
6. AI 结果写入后更新对应字段

**AI 分析复用**：
- 速读：复用 `content.py` 中 `chat_async` + 现有速读 prompt，传入 `content_snippet`
- 商业机会 / 研发机会：复用 `services/ai_processor.py` 中现有的分析函数

### 存储函数

在 `backend/services/storage.py` 末尾追加 `manual_intel` 相关 CRUD 函数：
- `get_manual_intel_items(source_platform=None)` → `List[Dict]`
- `get_manual_intel_item_by_id(id)` → `Optional[Dict]`
- `create_manual_intel_item(data)` → `Dict`
- `update_manual_intel_item(id, updates)` → `Optional[Dict]`（用于写入 AI 结果）
- `delete_manual_intel_item(id)` → `bool`

### main.py 注册

```python
from routers.manual_intel import router as manual_intel_router
app.include_router(manual_intel_router, prefix="/api/manual-intel", tags=["manual-intel"])
```

---

## 前端架构

### 新增文件

- `frontend/src/pages/ManualIntelPage.jsx` — 主页面
- `frontend/src/pages/ManualIntelPage.css`（如样式量大则拆出，否则内联）

### 路由

在 `frontend/src/App.jsx` 新增：
```jsx
import ManualIntelPage from './pages/ManualIntelPage'
// ...
<Route path="/manual-intel" element={<ManualIntelPage />} />
```

### 侧边栏入口

在 `frontend/src/components/Sidebar.jsx` 的"实验想法池"下方，分隔线后新增：
```jsx
<Link to="/manual-intel" className={`menu-item ${isActive('/manual-intel') ? 'active' : ''}`}>
  <span>📌</span><span>我的情报收藏</span>
</Link>
```

### 页面结构（ManualIntelPage.jsx）

```
┌─────────────────────────────────────────┐
│ 页头：📌 我的情报收藏  [3 条]             │
│ 副标题：手动录入的情报，自动生成速读与分析  │
├─────────────────────────────────────────┤
│ 录入区（白色卡片）                        │
│  [URL 输入框          ] [来源▼] [+录入] │
│  [备注输入框（可选）                    ] │
├─────────────────────────────────────────┤
│ 筛选栏：全部 / X / Reddit / Blog / ...  │
├─────────────────────────────────────────┤
│ 情报卡片列表（倒序，最新在上）            │
│  ┌──────────────────────────────────┐  │
│  │ 标题（链接）              [重分析] [删除] │
│  │ 来源标签  手动录入标签  时间      │
│  │ 备注（如有）                      │
│  │ ▼ 速读摘要（默认展开）            │
│  │ ▶ 商业机会（默认折叠）            │
│  │ ▶ 研发机会（默认折叠）            │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 交互细节

- **录入**：提交后立即在列表顶部插入新卡片（乐观更新），显示"AI 分析中…"占位符；前端每 3 秒轮询一次 `GET /api/manual-intel/{id}`，直到 `quick_read`、`business_opps`、`rdev_opps` 均非空后停止轮询并更新 UI
- **AI 分析状态**：每个分析区块有三态：loading（动画）/ 已完成（内容展开）/ 失败（显示重试按钮）
- **筛选**：点击来源标签 chip 筛选列表，纯前端过滤
- **删除**：直接删除，无确认弹窗（条目少，误删可重新录入）
- **重新分析**：点击后重新触发后端 AI 分析，覆盖现有结果

---

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `backend/routers/manual_intel.py` | 新增 | 5 个 API 端点 |
| `backend/services/storage.py` | 修改（追加） | manual_intel CRUD 函数 |
| `backend/main.py` | 修改 | 注册新路由 |
| `frontend/src/pages/ManualIntelPage.jsx` | 新增 | 主页面组件 |
| `frontend/src/components/Sidebar.jsx` | 修改 | 新增菜单入口 |
| `frontend/src/App.jsx` | 修改 | 新增路由 |

**数据目录**：`data/manual_intel/`（运行时自动创建）

---

## 不在本次范围内

- 批量导入（如书签文件）
- 手动情报与自动情报的关联/合并
- 手动情报出现在分享页面
- 搜索功能
