# last30days → SignalForge 内容导入设计

- 日期：2026-06-15
- 状态：设计已确认，待写实现计划
- 相关页面：`frontend/src/pages/SearchPage.jsx`（情报搜索）

## 目标

把 `last30days` 技能产出的「话题深度舆情报告」（Reddit / X / Hacker News /
YouTube / TikTok / Instagram 多源聚合）转换成 SignalForge 的 **content item**，
存入既有内容仓库，使其能通过现有 `/api/content` 被 **SearchPage** 搜索、筛选、
高亮、标签点击。

非目标：

- 不重写 SearchPage 的搜索逻辑（仅新增平台筛选 chip 的标签/配色）。
- 不替换或改造既有结构化情报（arxiv/github/model/news/blog/wechat）。
- 不把社交数据引入每日简报 / 机会看板流水线。

## 关键约束与已确认决策

1. **source_type 粒度 = 按平台拆分（A1）**：每个平台一个类型，对应 SearchPage 一个筛选 chip。
2. **wingsbot 通过 Python import 调用，不走 CLI 子进程**：使用
   `wingsbot.agent.loop.AgentLoop.process_direct(...)`，与 `wingsbot agent` 命令同一条代码路径。
3. **`hn` 而非 `hackernews`**：避免与 `FEED_SOURCE_TYPES` 中已有的 `hackernews`
   冲突，从而保证 last30days 数据不会泄漏进简报。
4. **解析器是健壮的、可独立测试的核心**：last30days 产出的 raw v3 markdown 格式确定，
   解析器对任何 v3 md 都可工作，完全不依赖 wingsbot。

## 架构（三层解耦）

```
[Layer 3] CLI: python cli.py import-last30days
   --topic "..."   → Layer 2（wingsbot 触发）→ 产出 raw v3 md → Layer 1
   --file <path>   → Layer 1（离线，跳过 wingsbot）
   --dir <dir>     → 批量 Layer 1（默认 ~/Documents/Last30Days/）
        │
[Layer 2] wingsbot 触发（in-process import）
   AgentLoop.process_direct("为话题 X 运行 last30days") → 技能写出
   ~/Documents/Last30Days/<slug>-raw-v3.md → 返回该文件路径
        │
[Layer 1] 解析器: backend/services/last30days_importer.py（纯函数，可测试）
   parse_last30days_markdown(text) -> list[item]
   import_last30days_file(path)    -> int   # 解析 + store_content_items()
```

### Layer 1 — 解析器 `backend/services/last30days_importer.py`

纯解析逻辑，无 wingsbot 依赖。对 `~/Documents/Last30Days/*.md` 现有样本直接单测。

公开函数：

- `parse_last30days_markdown(text: str) -> list[dict]`
  解析 raw v3 markdown，返回 content item 列表。
- `import_last30days_file(path: str | Path) -> int`
  读取文件 → 解析 → `store_content_items()`，返回新增条数。
- `import_last30days_dir(dir: str | Path = ~/Documents/Last30Days) -> int`
  遍历目录批量导入。

#### raw v3 markdown 结构（解析目标）

```
# last30days v3.x.x: <Topic>
- Date range: 2026-05-13 to 2026-06-12
- Sources: 3 active (Hacker News, Reddit, X)
## Ranked Evidence Clusters
### N. <cluster title> (score 58, 3 items, sources: Reddit, X)
- Uncertainty: ...
1. [x] <item title>
   - 2026-06-10 | @DataScienceDojo | [54likes, 9rt, 4re] | score:58
   - URL: https://x.com/...
   - Evidence: ...
   - u/<user> (37 upvotes): <comment>
   - Insight: ...
```

解析步骤：

1. 从 `# last30days ...: <Topic>` 抽取 `topic`。
2. 遍历每个 `### N. <title> (score X, ... )` 集群，记录 `cluster_title`、`cluster_score`。
3. 集群内每个编号项 `\d+. [platform] <title>` 生成一个 content item，
   读取其子行：`date | author | [engagement] | score:N`、`URL:`、`Evidence:`、评论行、`Insight:`。

#### 字段映射（last30days item → content item）

| content 字段        | 来源 |
|---------------------|------|
| `id`                | `l30-{platform}-{md5(url)[:12]}`；无 URL 时用 title 哈希 |
| `source_type`       | 平台 key（见下表） |
| `source`            | 平台显示名（"Reddit"/"X"/"Hacker News"…） |
| `title`             | 项标题 |
| `url`               | `URL:` 行 |
| `date` / `created_at` | 项日期（决定写入 `data/content/{date}.json`）；缺失时回退报告 Date range 末日 |
| `summary`           | `Evidence:` 文本（SearchPage 读取此字段） |
| `original_content`  | Evidence + Top 评论 + Insight |
| `relevance_score`   | `min(10, round(cluster_score / 6))`（集群分约 26–58 → 4–10） |
| `tags`              | `[topic, ...集群关键词]`（SearchPage 读取 + 标签点击搜索） |
| `category`          | `= tags`（与既有结构对齐） |
| `metadata`          | `{topic, cluster_title, cluster_score, author, engagement, comments, insight, origin: "last30days"}` |

平台映射：

| raw 标记        | source_type | source 显示名 |
|-----------------|-------------|---------------|
| `[reddit]`      | `reddit`    | Reddit        |
| `[x]`           | `x`         | X             |
| `[hackernews]`  | `hn`        | Hacker News   |
| `[youtube]`     | `youtube`   | YouTube       |
| `[tiktok]`      | `tiktok`    | TikTok        |
| `[instagram]`   | `instagram` | Instagram     |

未知标记 → `source_type = "social"`，`source = 原标记`。

### Layer 2 — wingsbot 触发（in-process）

放在 `backend/services/last30days_importer.py` 或同级 `last30days_wingsbot.py`。

调用方式（镜像 `wingsbot agent -m` 的代码路径）：

```python
from wingsbot.config.loader import load_config, get_data_dir
from wingsbot.bus.queue import MessageBus
from wingsbot.cron.service import CronService
from wingsbot.agent.loop import AgentLoop
from wingsbot.cli.commands import _make_provider  # 复用 provider 构造

config = load_config()
agent_loop = AgentLoop(
    bus=MessageBus(),
    provider=_make_provider(config),
    workspace=config.workspace_path,
    model=config.agents.defaults.model,
    temperature=config.agents.defaults.temperature,
    max_tokens=config.agents.defaults.max_tokens,
    max_iterations=config.agents.defaults.max_tool_iterations,
    memory_window=config.agents.defaults.memory_window,
    disabled_skills=config.agents.defaults.disabled_skills,
    cron_service=CronService(get_data_dir() / "cron" / "jobs.json"),
    # 其余参数按 cli/commands.py:agent 同样传入
)
response = await agent_loop.process_direct(
    f"使用 last30days 技能研究话题：{topic}，把原始结果写到 ~/Documents/Last30Days/",
    session_id="signalforge:last30days",
)
await agent_loop.close_mcp()
```

`process_direct` 为 async，SignalForge 同步 CLI 用 `asyncio.run(...)` 包裹。

产出定位：技能将 raw v3 md 写入 `~/Documents/Last30Days/<slug>-raw-v3.md`。
触发后取「该话题 slug 匹配且 mtime 最新」的文件交给 Layer 1。若找不到新文件，
回退解析 response 文本（v3 格式同样适用）并告警。

### Layer 3 — CLI `python cli.py import-last30days`

参数：

- `--topic "<topic>"`：触发 wingsbot 跑 last30days，再解析+入库（端到端）。
- `--file <path>`：直接解析既有 md，跳过 wingsbot（离线/回放）。
- `--dir <dir>`：批量解析目录，默认 `~/Documents/Last30Days/`。
- 至少需提供 `--topic`/`--file`/`--dir` 其一。

输出：打印解析条数、按平台分组的新增计数、去重跳过数。

### wingsbot 技能安装（一次性 setup）

把 `last30days` 安装到 `~/.wingsbot/workspace/skills/last30days/`，
SKILL.md 采用 wingsbot 兼容头（参考 `rss-daily-auto`）：

```yaml
---
name: last30days
description: ...
metadata: '{"wingsbot":{"skill_type":"research","callable_by_llm":true}}'
---
```

同时确保 last30days 运行时（`scripts/last30days.py` 及所需 API key）对 wingsbot
可见——技能源在 `~/.claude/plugins/marketplaces/last30days-skill/skills/last30days/`，
运行时缓存在 `~/.claude/plugins/cache/last30days-skill/`。

## 前端（SearchPage.jsx）

仅新增映射，无其它逻辑改动：

```js
const SOURCE_TYPE_LABELS = {
  // ...既有...
  reddit: 'Reddit', x: 'X', youtube: 'YouTube',
  tiktok: 'TikTok', instagram: 'Instagram', hn: 'Hacker News',
}
const SOURCE_TYPE_COLORS = {
  // ...既有...
  reddit:    { bg: '#fff7ed', color: '#c2410c' },
  x:         { bg: '#f1f5f9', color: '#0f172a' },
  youtube:   { bg: '#fef2f2', color: '#b91c1c' },
  tiktok:    { bg: '#f5f3ff', color: '#6d28d9' },
  instagram: { bg: '#fdf2f8', color: '#be185d' },
  hn:        { bg: '#fff7ed', color: '#ea580c' },
}
```

既有 `/api/content`、筛选 chip、关键词高亮、标签点击搜索均自动适配。

## 后端集成约束

- **wingsbot 可导入**：wingsbot 装在系统 Python
  (`/Users/shitaosun/Project/AI-opensource/wingsbot`)。SignalForge venv 需能
  `import wingsbot`——做法二选一：(a) 在 SignalForge venv 中
  `pip install -e /Users/shitaosun/Project/AI-opensource/wingsbot`；
  (b) 在 Layer 2 import 前插入该路径到 `sys.path`。优先 (a)。
  wingsbot import 失败时，`--topic` 触发应给出清晰报错并提示用 `--file`/`--dir`。
- **简报隔离**：新 source_type 均不在 `FEED_SOURCE_TYPES`
  (`backend/services/briefing_generator.py:10`)，社交数据不进简报；用 `hn` 规避冲突。
- **去重**：`store_content_items()` 按 `id` 去重，重复导入安全（幂等）。

## 错误处理

- 解析器：跳过缺 URL 且缺 title 的残缺项并计数；行格式异常时跳过该项不中断整文件。
- wingsbot：import 失败 / process_direct 异常 / 找不到产出文件 → 报错并建议离线路径。
- API key 耗尽（如 ScrapeCreators 402）：仅影响 wingsbot 抓取覆盖面，
  解析器对已产出报告不受影响（`--file`/`--dir` 始终可用）。

## 测试策略

- **解析器单测**（核心）：以 `~/Documents/Last30Days/*.md` 三个现有样本为夹具，
  断言条目数、平台映射、id 生成、relevance_score 归一、tags 含 topic、去重。
- **前端**：复用既有 SearchPage 测试模式，断言新平台 chip 渲染与配色。
- wingsbot 触发层不做联网单测（依赖外部 key），仅手动 / 集成验证。

## 交付物清单

1. `backend/services/last30days_importer.py`（Layer 1 + Layer 2）。
2. `backend/cli.py` 新增 `import-last30days` 子命令（Layer 3）。
3. `~/.wingsbot/workspace/skills/last30days/`（技能安装，一次性）。
4. `frontend/src/pages/SearchPage.jsx`（6 个平台标签/配色）。
5. 解析器单测 + 前端测试。
6. SignalForge venv 中 wingsbot 可导入（editable install）。
