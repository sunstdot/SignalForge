# 搜索页触发 last30days 实时研究 设计

- 日期：2026-06-15
- 状态：设计已确认，实现中
- 前置：`docs/superpowers/specs/2026-06-15-last30days-to-content-import-design.md`

## 目标

把 last30days 实时研究的触发入口从 CLI 移到「情报搜索」页：用户输入关键词点「搜索」，
**先查本地** `/api/content`；若该关键词本地无结果，则后台触发
`run_last30days_via_wingsbot(关键词)`，前端轮询任务状态，完成后自动展示新导入的结果。

## 已确认决策

1. **触发策略：先本地，空才实时拓**。只有关键词非空且本地 0 结果时才触发 last30days。
2. **异步：后台任务 + 轮询**。研究在后台线程跑（`run_last30days_via_wingsbot` 内部用
   `asyncio.run`，不能在 FastAPI 事件循环里直接调），API 立即返回 `job_id`，前端轮询。
3. **任务态文件持久化**：存到 `data/last30days/jobs.json`（进程内内存 + 文件，单机自用足够）。
4. **CLI 调整**：移除 `import-last30days --topic`（实时触发唯一入口 = 研究 API）；
   CLI 仅保留 `--file`/`--dir` 离线导入。

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

- 抽出 `fetchLocal(q, st) -> filtered`（拉 `/api/content` + 关键词过滤）。
- `doSearch`：调 `fetchLocal`；若 `filtered.length===0 && q.trim()` → 进入研究流程
  （不直接展示空态）；否则正常展示。
- `runResearch(topic, st)`：POST `/research` 拿 job_id，每 3s 轮询 `/research/{job_id}`，
  最多约 10 分钟；`done` → 再 `fetchLocal` 展示；`error` → 显示错误。用 ref token 保证
  新搜索会取消上一次轮询。
- 新增状态 `researching`、`researchError`。渲染优先级：loading → researching 面板
  （「本地没有『topic』，正在实时研究全网最近 30 天…（可能几分钟）」）→ researchError 面板
  → 正常结果/空态。

## 测试

- `test_last30days_jobs.py`：monkeypatch JOBS_FILE 到 tmp；create→running，
  finish(count)→done，finish(error)→error，get 不存在→None。
- `test_last30days_router.py`：FastAPI TestClient，patch
  `routers.last30days.run_last30days_via_wingsbot` + monkeypatch jobs 文件；
  POST 无 topic→400，POST 正常→running 且能轮询到 done(count)，GET 未知 job→404。
- `SearchPage.test.mjs`：断言源码含 `/api/last30days/research`、`researching`、
  本地空才触发的逻辑标记。
- CLI：更新 `test_cli_import_last30days.py`，移除 topic 用例，保留 file/dir。
