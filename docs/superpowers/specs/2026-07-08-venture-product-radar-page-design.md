# 创投产品雷达页面设计

- 日期：2026-07-08
- 状态：设计已确认，待实现
- 样例报告：`/Users/shitaosun/Documents/VentureProductRadar/radar-ai-sales-automation-startup-opportunities-20260708T134819Z.json`

## 目标

在 SignalForge 情报中心新增「创投产品雷达」页面，用于展示 `venture-product-radar`
skill 生成的 VC 投资、AI 产品、融资动态和市场信号报告。

页面采用「报告级为主，实体级为辅」的结构：

- 用户可以导入或运行一次 radar 研究，生成一份可回看的报告档案。
- 报告详情页按产品线索、融资动态、市场信号、来源证据、下一步跟踪展示原始 JSON 数据。
- 页面保留报告级上下文，不只展示导入 `data/content` 后的通用 content item。

## 已确认决策

1. **页面形态：两者结合**。既支持发起新扫描，也支持查看历史报告档案。
2. **历史单位：报告级为主，实体级为辅**。每次运行是一份报告；报告内部展示产品、融资、信号等实体。
3. **数据来源：基于原始 JSON 展示**。第一版直接读取并展示 `venture-product-radar.v2` 报告，不依赖现有 content importer 还原字段。
4. **第一版验收数据**：使用用户给定的本地 JSON 文件导入后，页面必须完整展示该报告。
5. **不做二次投资判断**。页面展示事实、信号分数、置信度、证据缺口和下一步跟踪，不额外生成投资 thesis。

## 样例报告结构

样例报告的关键字段：

- `schema_version`: `venture-product-radar.v2`
- `command`: `venture-radar`
- `mode`: `radar`
- `topic`: `AI sales automation startup opportunities`
- `generated_at`: `2026-07-08T13:47:59+00:00`
- `lookback_days`: `30`
- `products`: 30 条
- `funding_rounds`: 6 条
- `signals`: 39 条
- `source_links`: 60 条
- `research_plan`: 16 条
- `next_watch_items`: 10 条
- `errors_by_source`: `rss_feeds`、`gdelt` 有错误

需要特别保留的报告级字段：

- `source_strategy`
- `source_links`
- `evidence_conflicts`
- `errors_by_source`
- `research_plan`
- `next_watch_items`

这些字段不会完整进入当前 `data/content` 通用内容库，因此本功能需要独立的报告存储。

## 后端设计

### 存储位置

新增目录：

```text
data/venture_radar/reports/
data/venture_radar/index.json
```

`reports/<report_id>.json` 保存原始 radar JSON。第一版不裁剪字段，只在读取时做轻量摘要。

`index.json` 保存报告列表，结构：

```json
{
  "reports": [
    {
      "id": "radar-ai-sales-automation-startup-opportunities-20260708T134819Z",
      "topic": "AI sales automation startup opportunities",
      "mode": "radar",
      "command": "venture-radar",
      "generated_at": "2026-07-08T13:47:59+00:00",
      "lookback_days": 30,
      "counts": {
        "products": 30,
        "funding_rounds": 6,
        "companies": 0,
        "signals": 39,
        "source_links": 60,
        "next_watch_items": 10
      },
      "source_path": "/Users/shitaosun/Documents/VentureProductRadar/radar-ai-sales-automation-startup-opportunities-20260708T134819Z.json",
      "imported_at": "2026-07-08T14:30:00+08:00"
    }
  ]
}
```

`report_id` 由源文件名去掉 `.json` 得到；如果未来从后台运行直接产生报告，也使用生成文件名作为 id。

### 新增服务

新增 `backend/services/venture_radar_reports.py`：

- `import_venture_radar_report(path: str) -> Dict`
- `list_venture_radar_reports() -> List[Dict]`
- `load_venture_radar_report(report_id: str) -> Optional[Dict]`
- `summarize_venture_radar_report(report: Dict) -> Dict`

导入时校验：

- 文件必须存在。
- JSON 顶层必须是 object。
- `schema_version` 必须以 `venture-product-radar.` 开头。
- 必须包含 `topic`、`generated_at` 或可回退到文件名。

### 路由

扩展现有 `backend/routers/venture_radar.py`：

```text
GET  /api/venture-radar/reports
GET  /api/venture-radar/reports/{report_id}
POST /api/venture-radar/import-file
POST /api/venture-radar/research
GET  /api/venture-radar/research/{job_id}
```

`POST /import-file` body：

```json
{
  "path": "/Users/shitaosun/Documents/VentureProductRadar/radar-ai-sales-automation-startup-opportunities-20260708T134819Z.json"
}
```

返回导入后的 index entry。

一期必须实现 `import-file`，确保用户给定的本地 JSON 可以导入并展示。现有 `/research`
后台任务完成后，如果 `venture-product-radar` 返回了新生成的 JSON 路径，也同步调用同一套报告导入逻辑，
把原始报告保存到 `data/venture_radar/reports/`；如果研究任务只完成了 content item 导入但没有返回
原始报告路径，则 job 标记为 error，避免历史档案缺失。

## 前端设计

### 路由和导航

新增页面：

```text
frontend/src/pages/VentureRadarPage.jsx
```

新增路由：

```jsx
<Route path="/venture-radar" element={<VentureRadarPage />} />
```

Sidebar 新增入口，放在「情报搜索」附近：

```text
🛰️ 创投产品雷达
```

### 页面布局

第一屏是工作台，不做营销页。

顶部区域：

```text
创投产品雷达
AI sales automation startup opportunities
2026-07-08 · lookback 30 days · radar mode

[输入新主题] [综合雷达 ▼] [开始扫描]
[导入本地 JSON 路径] [导入]
```

概览指标：

```text
产品线索 30
融资事件 6
市场信号 39
来源链接 60
待跟踪 10
数据问题 2
```

主体结构：

```text
左侧：历史报告列表
右侧：当前报告详情

[产品线索] [融资动态] [市场信号] [来源证据] [下一步跟踪]
```

### 历史报告列表

每条报告显示：

- topic
- generated date
- mode
- 产品 / 融资 / 信号数量
- 是否有 source errors

点击报告后加载 `GET /api/venture-radar/reports/{id}`。

### 产品线索 tab

展示 `products`。卡片字段：

- `name`
- `launch_channel`
- `product_type`
- `traction_signals`
- `description`
- `confidence`
- `source_urls`
- `evidence_gaps`

样例验收：能看到 `JSONbored/awesome-claude`，并显示 `GitHub`、`open_source`、`stars: 278`、`confidence: low`。

### 融资动态 tab

展示 `funding_rounds`。卡片字段：

- `company_name`
- `amount`
- `announced_date`
- `market_signal`
- `officially_confirmed`
- `confidence`
- `source_urls`
- `evidence_gaps`

样例验收：能看到 `AI chip maker SambaNova`、`$1B`、`2026-07-07`。

### 市场信号 tab

展示 `signals`。卡片字段：

- `title`
- `signal_type`
- `signal_score`
- `signal_strength`
- `summary`
- `confidence`
- `source_urls`
- `evidence_gaps`

`summary` 可能包含 HTML。第一版可以安全地去除 HTML 标签并截断展示，详情区再显示纯文本摘要；不使用 `dangerouslySetInnerHTML` 渲染外部报告内容。

样例验收：能看到 `Railway secures $100 million to challenge AWS with AI-native cloud infrastructure`。

### 来源证据 tab

展示报告级证据：

- `source_strategy.primary_sources`
- `source_strategy.secondary_sources`
- `source_strategy.websearch_queries`
- `source_strategy.notes`
- `source_links`
- `evidence_conflicts`
- `errors_by_source`

错误来源需要突出但不阻塞展示。样例报告应显示：

- `rss_feeds: FinSMEs: HTTP Error 403: Forbidden`
- `gdelt: <urlopen error _ssl.c:983: The handshake operation timed out>`

### 下一步跟踪 tab

展示：

- `next_watch_items`
- `research_plan`

样例验收：能看到 10 条以 `Find primary product page` 开头的 follow-up。

### 筛选和详情

第一版提供轻量筛选：

- keyword 搜索：匹配标题、名称、摘要、描述。
- confidence 筛选：`all`、`high`、`medium`、`low`。
- signal type 筛选：仅在市场信号 tab 生效。

点击卡片打开详情面板，展示完整字段、来源链接和证据缺口。

## 错误与空态

- 无历史报告：显示导入 JSON 路径输入框和说明。
- 导入失败：显示后端返回的错误，比如文件不存在、JSON 非法、schema 不匹配。
- 报告某类实体为空：tab 内显示空态，不隐藏 tab。
- source errors：显示在来源证据 tab 和概览的「数据问题」指标里。
- research job 失败：沿用现有 job error 展示。

## 测试

### 后端

新增 `backend/tests/test_venture_radar_reports.py`：

- 导入样例结构后写入 `data/venture_radar/reports/<id>.json`。
- `index.json` 包含 topic、mode、counts。
- 非 JSON 文件返回错误。
- schema 不匹配返回错误。
- list reports 按 `generated_at` 倒序。

扩展 `backend/tests/test_venture_radar_router.py`：

- `POST /api/venture-radar/import-file` 成功返回 report entry。
- `GET /api/venture-radar/reports` 返回导入报告列表。
- `GET /api/venture-radar/reports/{id}` 返回完整原始报告。
- 未知 report id 返回 404。

### 前端

新增 `frontend/src/pages/VentureRadarPage.test.mjs`：

- 源码包含 `/api/venture-radar/reports` 和 `/api/venture-radar/import-file`。
- 页面包含产品、融资、市场信号、来源证据、下一步跟踪 tab 文案。
- 页面逻辑包含 `products`、`funding_rounds`、`signals`、`next_watch_items` 字段处理。
- summary 渲染路径包含 HTML strip 或纯文本化逻辑。

## 第一版验收标准

导入以下文件：

```text
/Users/shitaosun/Documents/VentureProductRadar/radar-ai-sales-automation-startup-opportunities-20260708T134819Z.json
```

页面必须展示：

- 报告主题：`AI sales automation startup opportunities`
- 产品线索：30
- 融资事件：6
- 市场信号：39
- 来源链接：60
- 错误来源：`rss_feeds`、`gdelt`
- 产品 tab：`JSONbored/awesome-claude`
- 融资 tab：`AI chip maker SambaNova` 和 `$1B`
- 信号 tab：`Railway secures $100 million to challenge AWS with AI-native cloud infrastructure`
- 下一步跟踪 tab：10 条以 `Find primary product page` 开头的条目

## 不在本次范围

- 生成二次投资 thesis、竞品分析或商业模式评分。
- 跨报告实体去重和公司画像合并。
- 将某个产品或融资条目保存到实验想法池。
- 静态部署模式下的 venture radar 缓存导出。
- 对外部来源 HTML 做富文本渲染。
- 自动定时运行 venture radar。
