# 情报搜索 · brief 合成与串联 设计

- 日期：2026-06-16
- 状态：设计已确认，实现中
- 前置：`2026-06-15-last30days-to-content-import-design.md`、`2026-06-15-search-triggered-last30days-design.md`

## 目标

点「情报搜索」只显示搜索框；输入 topic 点搜索 → 实时跑 last30days → 后端把抓到的条目
**聚合 + LLM 合成**成一个 `brief` 对象 → 前端用现有叙事仪表盘（`SearchPage.jsx` + `SAMPLE_BRIEF` 形状）渲染。

## 已确认决策
1. 一次做全：机械聚合 + LLM 合成叙事。
2. 数据实时来自 last30days（沿用异步 job + 轮询）。

## brief 字段两类来源

**A. 机械聚合（确定性，可单测）**
- `meta`：total / platforms{x,reddit,hn} / window / featured(score≥阈值数)
- `dashboard.tiles`：每平台 count + 互动和；`dashboard.volume`：按 volume 归一百分比
- `voices`：按 volume 排序的 author 去重 Top N
- `caveat`：哪些平台 0 结果
- `timeline[]`：按 date 分组；每条 → {p, who, handle, score, title, sum, tags, stat}
- `rawNote`：原始 md 路径

**B. LLM 合成（叙事，喂聚类/条目，输出 JSON）**
- `headline / kicker / lede / consensus{left,right,labels}`
- `themes[]{n,title,html} / patterns[]{n,text,src,lead,wide} / deepDive[]{k,q,a}`
- 每条 timeline 的 `reason`（推荐理由）、`dashboard.insight`
- 合成失败 → 降级：headline=topic、themes 取 top cluster 标题、其余留空，页面仍可渲染。

## 数据字段变化（导入器）

raw v3 meta 行：`   - <date> | <author> | [<engagement>] | score:N`（youtube 的 author 是 dict）。
`last30days_importer.py` 现在丢掉了 author/engagement，需补进 metadata：
- `metadata.author`（@handle / r/sub / 站点名；youtube 取 dict 的 handle/title）
- `metadata.engagement`（原始串，如 `54likes, 9rt`）
- `metadata.volume`（engagement 里数字之和，用于排序/声量%）

## 组件

1. `services/last30days_importer.py` — 解析 meta 行时多抓 author/engagement/volume 进 metadata。
2. `services/last30days_brief.py`
   - `aggregate_brief(items, topic, platforms_zero) -> dict`（A，纯函数，单测）
   - `synthesize_narrative(items, topic) -> dict`（B，LLM，带 JSON 解析 + 降级）
   - `build_brief(topic) -> dict`：取 content 库中 `metadata.topic==topic` 的 last30days 条目 → A + B 合并 → 落 `data/last30days/briefs/<slug>.json`
3. `routers/last30days.py` — `POST /api/search/brief {topic}`：起 job → `run_last30days_via_wingsbot(topic)` 再 `build_brief(topic)` → job 完成；`GET /api/search/brief/{job_id}` 返回 {status, brief?}。复用 `last30days_jobs`（job 增加 `brief` 字段）。
4. `frontend/src/pages/SearchPage.jsx` — 默认空态（仅搜索框）；搜索 → POST → 轮询 → done 用返回的 brief 渲染（不再默认渲染 SAMPLE_BRIEF；保留为加载兜底/类型参考）。

## 流程
```
点情报搜索 → 空态(搜索框)
输入 topic → POST /api/search/brief → job_id
后端 job：run last30days(topic) → build_brief(topic)=aggregate+synthesize → 存 brief → done
前端轮询 GET → done 拿 brief → 渲染仪表盘；error → 错误态
```

## 测试
- 导入器：meta 行抓到 author/engagement/volume（含 youtube dict、reddit、纯 cmt）。
- aggregate_brief：给定假 items → meta/dashboard/voices/timeline/caveat 正确。
- synthesize_narrative：mock LLM 返回合法 JSON → 字段映射；返回坏 JSON → 降级不抛。
- brief 路由：job 跑通（stub run+build）→ 轮询到 done 带 brief；坏 topic→400。
- 前端：空态只有搜索框；搜索调 `/api/search/brief` 并渲染返回的 brief。
