# 搜索页触发 last30days 实时研究 设计

- 日期：2026-06-15
- 状态：设计已确认，实现中
- 前置：`docs/superpowers/specs/2026-06-15-last30days-to-content-import-design.md`

## 目标

把 last30days 实时研究的触发入口从 CLI 移到「情报搜索」页：用户输入关键词点「搜索」，
**先查本地** `/api/content`；若该关键词本地无结果，则后台触发
`run_last30days_via_wingsbot(关键词)`，前端轮询任务状态，完成后自动展示新导入的结果。

## 已确认决策

> 更新（2026-06-15 二次调整）：触发策略由「先本地、空才拓」改为「**每次搜索直接调
> last30days，不查本地情报**」；只展示该话题的 last30days 结果；展示沿用 SearchPage 卡片列表；
> 平台筛选 chip 限定 6 个社交来源。

1. **触发策略：直接调 last30days**。点搜索即对关键词跑 last30days，不查本地 AI 情报。
2. **异步：后台任务 + 轮询**。研究在后台线程跑（`run_last30days_via_wingsbot` 内部用
   `asyncio.run`，不能在 FastAPI 事件循环里直接调），API 立即返回 `job_id`，前端轮询。
3. **任务态文件持久化**：存到 `data/last30days/jobs.json`（进程内内存 + 文件，单机自用足够）。
4. **CLI 调整**：移除 `import-last30days --topic`（实时触发唯一入口 = 研究 API）；
   CLI 仅保留 `--file`/`--dir` 离线导入。
5. **展示**：沿用 `SearchPage.jsx` 卡片列表（来源徽标 + 日期 + 标题 + 摘要 + 标签），
   只渲染 `metadata.origin === "last30days"` 且匹配话题的条目；平台 chip 限
   `reddit/x/hn/youtube/tiktok/instagram`，切换时本地重过滤不重复触发研究。

## 后端

### 任务存储 `backend/services/last30days_jobs.py`

文件：`data/last30days/jobs.json`，结构 `{job_id: job}`，job 字段：
`job_id, topic, status(running|done|error), count, error, started_at, finished_at`。
用 `threading.Lock` 包裹读改写，避免后台线程与请求并发写冲突。

函数：
- `create_job(topic) -> job_id`（status=running）
- `finish_job(job_id, *, count=None, error=None)`（error 非空则 status=error，否则 done）
- `get_job(job_id) -> dict | None`

### 路由 `backend/routers/last30days.py`（prefix `/api/last30days`）

- `POST /research` body `{topic}`：topic 必填（空 → 400）。`create_job`，起
  `daemon` 线程跑 `run_last30days_via_wingsbot(topic)`，成功 `finish_job(count=n)`，
  异常 `finish_job(error=...)`。返回 `{job_id, status:"running", topic}`。
- `GET /research/{job_id}`：返回 job（不存在 → 404）。

在 `main.py` 注册：`app.include_router(last30days_router, prefix="/api/last30days")`。

## 前端 `frontend/src/pages/SearchPage.jsx`

- `fetchTopicResults(topic, st) -> items`：拉 `/api/content`（可带 `source_type`），
  过滤到 `metadata.origin==='last30days'` 且话题匹配（title/summary/tags/metadata.topic）。
- `doSearch(q, st)`：关键词非空才执行，直接 `runResearch`（不查本地、不先展示）。
- `runResearch(topic, st, token)`：POST `/research` 拿 job_id，每 3s 轮询，最多约 10 分钟；
  `done` → `fetchTopicResults` 展示；`error` → 显示错误。ref token 保证新搜索取消旧轮询。
- `handleTypeChange`：平台 chip 切换时对 `lastTopicRef` 的话题本地重过滤，不重复触发研究。
- 平台 chip 仅渲染 `L30_TYPES = [reddit, x, hn, youtube, tiktok, instagram]`。
- 状态 `researching`、`researchTopic`、`researchError`。渲染：researching 面板
  （「正在实时研究『topic』最近 30 天的讨论…」）→ researchError 面板 → 结果卡片列表/空态。

## 测试

- `test_last30days_jobs.py`：monkeypatch JOBS_FILE 到 tmp；create→running，
  finish(count)→done，finish(error)→error，get 不存在→None。
- `test_last30days_router.py`：FastAPI TestClient，patch
  `routers.last30days.run_last30days_via_wingsbot` + monkeypatch jobs 文件；
  POST 无 topic→400，POST 正常→running 且能轮询到 done(count)，GET 未知 job→404。
- `SearchPage.test.mjs`：断言源码含 `/api/last30days/research`、`researching`、
  本地空才触发的逻辑标记。
- CLI：更新 `test_cli_import_last30days.py`，移除 topic 用例，保留 file/dir。
