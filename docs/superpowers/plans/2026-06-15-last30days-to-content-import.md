# last30days → 内容导入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `last30days` 技能产出的舆情报告解析成 SignalForge content item，存入既有内容仓库，让 SearchPage 可搜索/筛选；wingsbot 通过 Python import（非 CLI 子进程）触发。

**Architecture:** 三层解耦——(L1) 纯解析器 `last30days_importer.py` 把 raw v3 markdown 转 content item 并入库；(L2) 同模块的 wingsbot 触发函数用 `AgentLoop.process_direct` 跑 last30days 再调 L1；(L3) `cli.py` 的 `import-last30days` 子命令暴露 `--topic/--file/--dir`。前端仅给 SearchPage 补 6 个平台的标签/配色。

**Tech Stack:** Python 3.12 / FastAPI / pytest(asyncio_mode=auto) 后端；React + Vite 前端，测试用 `node --test` `.test.mjs`；wingsbot 可编辑安装包。

参考 spec：`docs/superpowers/specs/2026-06-15-last30days-to-content-import-design.md`

---

### Task 1: 让 wingsbot 在 SignalForge venv 中可导入

**Files:**
- Modify: `backend/requirements.txt`（追加注释说明）

- [ ] **Step 1: 在 SignalForge venv 安装 wingsbot（editable）**

Run:
```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge/backend && \
  ./venv/bin/pip install -e /Users/shitaosun/Project/AI-opensource/wingsbot
```
Expected: `Successfully installed wingsbot-0.1.4...`（或 `already satisfied`）

- [ ] **Step 2: 验证可导入**

Run:
```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge/backend && \
  ./venv/bin/python -c "import wingsbot; from wingsbot.agent.loop import AgentLoop; print('ok', wingsbot.__file__)"
```
Expected: 打印 `ok /Users/shitaosun/Project/AI-opensource/wingsbot/wingsbot/__init__.py`

- [ ] **Step 3: 在 requirements.txt 记录该依赖来源**

在 `backend/requirements.txt` 末尾追加：
```
# wingsbot 为本地可编辑安装，触发 last30days 用：
# pip install -e /Users/shitaosun/Project/AI-opensource/wingsbot
```

- [ ] **Step 4: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge && \
  git add backend/requirements.txt && \
  git commit -m "chore: document wingsbot editable dependency for last30days import"
```

---

### Task 2: 解析器核心 `parse_last30days_markdown`

**Files:**
- Create: `backend/services/last30days_importer.py`
- Test: `backend/tests/test_last30days_importer.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_last30days_importer.py`:
```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.last30days_importer import parse_last30days_markdown

SAMPLE = """# last30days v3.3.2: Loop Engineering
- Date range: 2026-05-13 to 2026-06-12
- Sources: 2 active (Reddit, X)
## Ranked Evidence Clusters
### 1. Loop engineering takes over (score 58, 2 items, sources: Reddit, X)
1. [x] You should design loops that prompt your agents
   - 2026-06-10 | @DataScienceDojo | [54likes, 9rt] | score:58
   - URL: https://x.com/DataScienceDojo/status/2064739436395434269
   - Evidence: You shouldn't be prompting coding agents anymore.
2. [reddit] Is loop engineering just cron?
   - 2026-06-11 | r/singularity | [396upvotes] | score:50
   - URL: https://www.reddit.com/r/singularity/comments/abc/
   - Evidence: This is just a workflow that runs on a schedule.
### 2. Token cost worries (score 30, 1 item, sources: Hacker News)
1. [hackernews] Running loops overnight burns tokens
   - 2026-06-05 | dang | [120points] | score:30
   - URL: https://news.ycombinator.com/item?id=999
   - Evidence: Token usage can be orders of magnitude higher.
"""


class ParseTest(unittest.TestCase):
    def test_parses_all_items_with_fields(self):
        items = parse_last30days_markdown(SAMPLE)
        self.assertEqual(len(items), 3)

        x = items[0]
        self.assertEqual(x["source_type"], "x")
        self.assertEqual(x["source"], "X")
        self.assertEqual(x["title"], "You should design loops that prompt your agents")
        self.assertEqual(x["url"], "https://x.com/DataScienceDojo/status/2064739436395434269")
        self.assertEqual(x["date"], "2026-06-10")
        self.assertEqual(x["created_at"], "2026-06-10")
        self.assertTrue(x["summary"].startswith("You shouldn't"))
        self.assertEqual(x["relevance_score"], 10)  # min(10, round(58/6))
        self.assertEqual(x["tags"], ["Loop Engineering"])
        self.assertEqual(x["metadata"]["origin"], "last30days")
        self.assertEqual(x["metadata"]["cluster_score"], 58)
        self.assertTrue(x["id"].startswith("l30-x-"))

    def test_platform_mapping_hackernews_to_hn(self):
        items = parse_last30days_markdown(SAMPLE)
        hn = items[2]
        self.assertEqual(hn["source_type"], "hn")
        self.assertEqual(hn["source"], "Hacker News")
        self.assertEqual(hn["relevance_score"], 5)  # min(10, round(30/6))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_last30days_importer.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'services.last30days_importer'`

- [ ] **Step 3: 实现解析器**

Create `backend/services/last30days_importer.py`:
```python
"""last30days raw v3 markdown → SignalForge content items."""
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional

# raw 平台标记 -> (source_type, 显示名)
PLATFORM_MAP = {
    "reddit": ("reddit", "Reddit"),
    "x": ("x", "X"),
    "hackernews": ("hn", "Hacker News"),
    "youtube": ("youtube", "YouTube"),
    "tiktok": ("tiktok", "TikTok"),
    "instagram": ("instagram", "Instagram"),
}

_TOPIC_RE = re.compile(r"^#\s+last30days[^:]*:\s*(.+?)\s*$")
_RANGE_RE = re.compile(r"Date range:\s*\S+\s+to\s+(\d{4}-\d{2}-\d{2})")
_CLUSTER_RE = re.compile(r"^###\s+\d+\.\s*(.+?)\s*\(score\s+(\d+),")
_ITEM_RE = re.compile(r"^\d+\.\s*\[(\w+)\]\s*(.+?)\s*$")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_URL_RE = re.compile(r"^\s*-\s*URL:\s*(\S+)")
_EVIDENCE_RE = re.compile(r"^\s*-\s*Evidence:\s*(.+?)\s*$")


def _make_id(platform_key: str, url: str, title: str) -> str:
    basis = url or title
    return f"l30-{platform_key}-{hashlib.md5(basis.encode('utf-8')).hexdigest()[:12]}"


def parse_last30days_markdown(text: str) -> List[Dict]:
    """把 raw v3 markdown 解析成 content item 列表。"""
    topic = ""
    fallback_date: Optional[str] = None
    cluster_title = ""
    cluster_score = 0
    cur: Optional[Dict] = None
    items: List[Dict] = []

    def flush() -> None:
        nonlocal cur
        if not cur or (not cur.get("url") and not cur.get("title")):
            cur = None
            return
        platform_key, source_name = PLATFORM_MAP.get(
            cur["platform"], ("social", cur["platform"])
        )
        date = cur.get("date") or fallback_date
        score = min(10, round(cluster_score / 6))
        items.append({
            "id": _make_id(platform_key, cur.get("url", ""), cur["title"]),
            "source": source_name,
            "source_type": platform_key,
            "title": cur["title"],
            "url": cur.get("url", ""),
            "summary": cur.get("evidence", ""),
            "original_content": cur.get("evidence", ""),
            "relevance_score": score,
            "tags": [topic] if topic else [],
            "category": [topic] if topic else [],
            "date": date,
            "created_at": date,
            "metadata": {
                "topic": topic,
                "cluster_title": cluster_title,
                "cluster_score": cluster_score,
                "origin": "last30days",
            },
        })
        cur = None

    for line in text.splitlines():
        m = _TOPIC_RE.match(line)
        if m:
            topic = m.group(1)
            continue
        m = _RANGE_RE.search(line)
        if m:
            fallback_date = m.group(1)
            continue
        m = _CLUSTER_RE.match(line)
        if m:
            flush()
            cluster_title, cluster_score = m.group(1), int(m.group(2))
            continue
        m = _ITEM_RE.match(line)
        if m:
            flush()
            cur = {"platform": m.group(1).lower(), "title": m.group(2)}
            continue
        if cur is None:
            continue
        m = _URL_RE.match(line)
        if m:
            cur["url"] = m.group(1)
            continue
        m = _EVIDENCE_RE.match(line)
        if m:
            cur["evidence"] = m.group(1)
            continue
        if "| score:" in line and "date" not in cur:
            dm = _DATE_RE.search(line)
            if dm:
                cur["date"] = dm.group(1)

    flush()
    return items
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_last30days_importer.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge && \
  git add backend/services/last30days_importer.py backend/tests/test_last30days_importer.py && \
  git commit -m "feat: parse last30days v3 markdown into content items"
```

---

### Task 3: 文件 / 目录导入并入库

**Files:**
- Modify: `backend/services/last30days_importer.py`
- Test: `backend/tests/test_last30days_importer.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_last30days_importer.py` 顶部 import 处追加：
```python
import tempfile
from unittest.mock import patch
from services.last30days_importer import import_last30days_file, import_last30days_dir
```
并在文件末尾 `if __name__` 之前追加：
```python
class ImportFileTest(unittest.TestCase):
    def test_file_parses_and_stores(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(SAMPLE)
            path = f.name
        captured = {}
        def fake_store(items):
            captured["items"] = items
            return len(items)
        with patch("services.last30days_importer.store_content_items", side_effect=fake_store):
            n = import_last30days_file(path)
        self.assertEqual(n, 3)
        self.assertEqual(len(captured["items"]), 3)

    def test_dir_imports_all_md(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.md").write_text(SAMPLE, encoding="utf-8")
            (Path(d) / "b.md").write_text(SAMPLE, encoding="utf-8")
            with patch("services.last30days_importer.store_content_items",
                       side_effect=lambda items: len(items)):
                n = import_last30days_dir(d)
        self.assertEqual(n, 6)
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_last30days_importer.py -v`
Expected: FAIL，`ImportError: cannot import name 'import_last30days_file'`

- [ ] **Step 3: 实现导入函数**

在 `backend/services/last30days_importer.py` 顶部 import 区追加：
```python
from services.storage import store_content_items
```
并在文件末尾追加：
```python
DEFAULT_L30_DIR = Path.home() / "Documents" / "Last30Days"


def import_last30days_file(path) -> int:
    """解析单个 raw v3 markdown 文件并入库，返回新增条数。"""
    text = Path(path).read_text(encoding="utf-8")
    return store_content_items(parse_last30days_markdown(text))


def import_last30days_dir(directory=None) -> int:
    """批量导入目录下所有 .md（默认 ~/Documents/Last30Days），返回新增条数。"""
    directory = Path(directory) if directory else DEFAULT_L30_DIR
    total = 0
    for p in sorted(directory.glob("*.md")):
        total += import_last30days_file(p)
    return total
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_last30days_importer.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge && \
  git add backend/services/last30days_importer.py backend/tests/test_last30days_importer.py && \
  git commit -m "feat: add file/dir import for last30days reports"
```

---

### Task 4: wingsbot 触发层（in-process import）

**Files:**
- Modify: `backend/services/last30days_importer.py`
- Test: `backend/tests/test_last30days_importer.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_last30days_importer.py` 末尾 `if __name__` 之前追加：
```python
class WingsbotTriggerTest(unittest.TestCase):
    def test_run_imports_newest_report(self):
        # 不真正联网：打桩 _trigger_wingsbot 返回一个临时报告文件
        from services import last30days_importer as mod
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(SAMPLE)
            path = Path(f.name)
        with patch.object(mod, "_trigger_wingsbot", return_value=path):
            with patch("services.last30days_importer.store_content_items",
                       side_effect=lambda items: len(items)):
                n = mod.run_last30days_via_wingsbot("Loop Engineering")
        self.assertEqual(n, 3)

    def test_newest_report_since_picks_latest(self):
        from services import last30days_importer as mod
        import time
        with tempfile.TemporaryDirectory() as d:
            old = Path(d) / "old.md"; old.write_text("x", encoding="utf-8")
            time.sleep(0.01)
            start = time.time()
            time.sleep(0.01)
            new = Path(d) / "new.md"; new.write_text("y", encoding="utf-8")
            with patch.object(mod, "L30_OUTPUT_DIR", Path(d)):
                picked = mod._newest_report_since(start)
        self.assertEqual(picked.name, "new.md")
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_last30days_importer.py -v`
Expected: FAIL，`AttributeError: ... has no attribute 'run_last30days_via_wingsbot'`

- [ ] **Step 3: 实现触发层**

在 `backend/services/last30days_importer.py` 顶部 import 区追加：
```python
import asyncio
import time
```
并在文件末尾追加：
```python
L30_OUTPUT_DIR = DEFAULT_L30_DIR

_WINGSBOT_PATH = "/Users/shitaosun/Project/AI-opensource/wingsbot"


def run_last30days_via_wingsbot(topic: str) -> int:
    """通过 wingsbot 触发 last30days，再导入产出的最新报告，返回新增条数。"""
    md_path = _trigger_wingsbot(topic)
    return import_last30days_file(md_path)


def _newest_report_since(start: float):
    if not L30_OUTPUT_DIR.exists():
        return None
    cands = [p for p in L30_OUTPUT_DIR.glob("*.md") if p.stat().st_mtime >= start - 1]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def _trigger_wingsbot(topic: str) -> Path:
    try:
        from wingsbot.config.loader import load_config, get_data_dir
        from wingsbot.bus.queue import MessageBus
        from wingsbot.cron.service import CronService
        from wingsbot.agent.loop import AgentLoop
        from wingsbot.cli.commands import _make_provider
    except ImportError as e:
        raise RuntimeError(
            "wingsbot 不可导入。请在 SignalForge venv 执行 "
            f"`pip install -e {_WINGSBOT_PATH}`，或改用 --file/--dir 离线导入。"
        ) from e

    start = time.time()
    config = load_config()
    d = config.agents.defaults
    agent_loop = AgentLoop(
        bus=MessageBus(),
        provider=_make_provider(config),
        workspace=config.workspace_path,
        model=d.model,
        temperature=d.temperature,
        max_tokens=d.max_tokens,
        max_iterations=d.max_tool_iterations,
        memory_window=d.memory_window,
        disabled_skills=d.disabled_skills,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        cron_service=CronService(get_data_dir() / "cron" / "jobs.json"),
        restrict_to_workspace=config.tools.restrict_to_workspace,
        mcp_servers=config.tools.mcp_servers,
    )
    prompt = (
        f"使用 last30days 技能研究话题：{topic}。"
        f"完成后把原始结果（raw v3 markdown）保存到 {L30_OUTPUT_DIR}/。"
    )

    async def _run():
        try:
            return await agent_loop.process_direct(prompt, session_id="signalforge:last30days")
        finally:
            await agent_loop.close_mcp()

    response = asyncio.run(_run())
    md_path = _newest_report_since(start)
    if md_path is None:
        raise RuntimeError(
            "wingsbot 未产出 last30days 报告文件。agent 返回（节选）：\n"
            + (response or "")[:500]
        )
    return md_path
```

注意：`L30_OUTPUT_DIR = DEFAULT_L30_DIR` 必须放在 `DEFAULT_L30_DIR` 定义之后（Task 3 已定义在文件较前位置，此处在文件末尾追加，顺序成立）。

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_last30days_importer.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge && \
  git add backend/services/last30days_importer.py backend/tests/test_last30days_importer.py && \
  git commit -m "feat: trigger last30days via wingsbot in-process import"
```

---

### Task 5: CLI 子命令 `import-last30days`

**Files:**
- Modify: `backend/cli.py`
- Test: `backend/tests/test_cli_import_last30days.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_cli_import_last30days.py`:
```python
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


class ImportLast30daysCliTest(unittest.TestCase):
    def test_file_mode_calls_file_importer(self):
        with patch("services.last30days_importer.import_last30days_file", return_value=3) as imp:
            cli.cmd_import_last30days(Namespace(topic=None, file="/tmp/x.md", dir=None))
        imp.assert_called_once_with("/tmp/x.md")

    def test_topic_mode_calls_wingsbot(self):
        with patch("services.last30days_importer.run_last30days_via_wingsbot", return_value=5) as run:
            cli.cmd_import_last30days(Namespace(topic="Loop Engineering", file=None, dir=None))
        run.assert_called_once_with("Loop Engineering")

    def test_default_dir_mode(self):
        with patch("services.last30days_importer.import_last30days_dir", return_value=6) as imp:
            cli.cmd_import_last30days(Namespace(topic=None, file=None, dir=None))
        imp.assert_called_once_with(None)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_cli_import_last30days.py -v`
Expected: FAIL，`AttributeError: module 'cli' has no attribute 'cmd_import_last30days'`

- [ ] **Step 3: 实现 cmd 与子命令注册**

在 `backend/cli.py` 中，`cmd_share_page` 函数之后（约 367 行 `def main()` 之前）新增：
```python
def cmd_import_last30days(args):
    """导入 last30days 报告为可搜索情报"""
    from services.last30days_importer import (
        import_last30days_dir,
        import_last30days_file,
        run_last30days_via_wingsbot,
    )
    if args.topic:
        n = run_last30days_via_wingsbot(args.topic)
        print(f"✅ 话题「{args.topic}」导入 {n} 条情报")
    elif args.file:
        n = import_last30days_file(args.file)
        print(f"✅ 从 {args.file} 导入 {n} 条情报")
    else:
        n = import_last30days_dir(args.dir)
        print(f"✅ 批量导入 {n} 条情报")
```

在 `backend/cli.py` 的 `main()` 内、`args = parser.parse_args()` 之前（紧跟 `share_parser ...set_defaults` 那段之后）新增：
```python
    # import-last30days：把 last30days 报告转为可搜索情报
    l30_parser = subparsers.add_parser("import-last30days", help="导入 last30days 报告为可搜索情报")
    l30_parser.add_argument("--topic", help="话题：通过 wingsbot 触发 last30days 后导入")
    l30_parser.add_argument("--file", help="解析单个 raw v3 markdown 文件")
    l30_parser.add_argument("--dir", help="批量解析目录（默认 ~/Documents/Last30Days）")
    l30_parser.set_defaults(func=cmd_import_last30days)
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_cli_import_last30days.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge && \
  git add backend/cli.py backend/tests/test_cli_import_last30days.py && \
  git commit -m "feat: add import-last30days CLI command"
```

---

### Task 6: 前端 SearchPage 增加 6 个平台标签/配色

**Files:**
- Modify: `frontend/src/pages/SearchPage.jsx:3-19`
- Test: `frontend/src/pages/SearchPage.test.mjs`

- [ ] **Step 1: 写失败测试**

Create `frontend/src/pages/SearchPage.test.mjs`:
```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./SearchPage.jsx', import.meta.url), 'utf8')

test('SearchPage exposes last30days social source types', () => {
  for (const label of ['Reddit', 'YouTube', 'TikTok', 'Instagram', 'Hacker News']) {
    assert.match(source, new RegExp(label))
  }
  for (const key of ['reddit:', 'youtube:', 'tiktok:', 'instagram:', 'hn:']) {
    assert.match(source, new RegExp(key))
  }
})
```

- [ ] **Step 2: 运行确认失败**

Run: `node --test frontend/src/pages/SearchPage.test.mjs`
Expected: FAIL（找不到 `YouTube` / `hn:` 等）

- [ ] **Step 3: 增加标签与配色**

在 `frontend/src/pages/SearchPage.jsx` 把 `SOURCE_TYPE_LABELS`（第 3-10 行）改为：
```js
const SOURCE_TYPE_LABELS = {
  arxiv: '论文',
  github: '仓库',
  model: '模型',
  news: '资讯',
  blog: 'AI公司博客',
  wechat: '微信公众号',
  reddit: 'Reddit',
  x: 'X',
  hn: 'Hacker News',
  youtube: 'YouTube',
  tiktok: 'TikTok',
  instagram: 'Instagram',
}
```
把 `SOURCE_TYPE_COLORS`（第 12-19 行）改为：
```js
const SOURCE_TYPE_COLORS = {
  arxiv:  { bg: '#eef2ff', color: '#4338ca' },
  github: { bg: '#f0fdf4', color: '#166534' },
  model:  { bg: '#fdf4ff', color: '#7e22ce' },
  news:   { bg: '#fff7ed', color: '#c2410c' },
  blog:   { bg: '#f0f9ff', color: '#0369a1' },
  wechat: { bg: '#f0fdf4', color: '#15803d' },
  reddit:    { bg: '#fff7ed', color: '#c2410c' },
  x:         { bg: '#f1f5f9', color: '#0f172a' },
  hn:        { bg: '#fff7ed', color: '#ea580c' },
  youtube:   { bg: '#fef2f2', color: '#b91c1c' },
  tiktok:    { bg: '#f5f3ff', color: '#6d28d9' },
  instagram: { bg: '#fdf2f8', color: '#be185d' },
}
```

- [ ] **Step 4: 运行确认通过**

Run: `node --test frontend/src/pages/SearchPage.test.mjs`
Expected: 1 pass

- [ ] **Step 5: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge && \
  git add frontend/src/pages/SearchPage.jsx frontend/src/pages/SearchPage.test.mjs && \
  git commit -m "feat: add last30days social platform filters to SearchPage"
```

---

### Task 7: 把 last30days 技能安装进 wingsbot（一次性 setup）

**Files:**
- Create: `~/.wingsbot/workspace/skills/last30days/SKILL.md`

> 说明：这是环境配置任务，不含单测；依赖外部 API key，仅做安装与连通性验证。技能源在
> `~/.claude/plugins/marketplaces/last30days-skill/skills/last30days/`，运行时缓存在
> `~/.claude/plugins/cache/last30days-skill/`。

- [ ] **Step 1: 拷贝技能源到 wingsbot 工作区**

Run:
```bash
mkdir -p ~/.wingsbot/workspace/skills/last30days && \
cp -R ~/.claude/plugins/marketplaces/last30days-skill/skills/last30days/. \
      ~/.wingsbot/workspace/skills/last30days/
```
Expected: 无报错；`ls ~/.wingsbot/workspace/skills/last30days/SKILL.md` 存在

- [ ] **Step 2: 改写为 wingsbot 兼容的 front matter**

把 `~/.wingsbot/workspace/skills/last30days/SKILL.md` 顶部 YAML front matter（`---` 包裹的头部）替换为：
```yaml
---
name: last30days
description: Research what people say about a topic in the last 30 days across Reddit, X, Hacker News, YouTube, TikTok, Instagram. Saves a raw v3 markdown report to ~/Documents/Last30Days/.
metadata: '{"wingsbot":{"skill_type":"research","callable_by_llm":true}}'
---
```
（保留 front matter 之后的全部正文不动。）

- [ ] **Step 3: 验证 wingsbot 能识别该技能**

Run: `wingsbot agent -m "列出你当前可用的 skills，必须包含 last30days" --no-markdown`
Expected: 输出中出现 `last30days`

- [ ] **Step 4: Commit（仅文档记录，不提交家目录文件）**

在 `docs/superpowers/specs/2026-06-15-last30days-to-content-import-design.md` 同目录无需改动；本步骤无仓库内文件变更，跳过 commit。
若希望追踪安装步骤，可在 `backend/docs/` 下新增 `last30days-wingsbot-setup.md` 记录上述命令后再 commit。

---

## 端到端验证（全部任务完成后）

- [ ] **离线路径**：`cd backend && ./venv/bin/python cli.py import-last30days --file ~/Documents/Last30Days/peter-steinberger-raw-v3.md`
  预期打印 `✅ 从 ... 导入 N 条情报`（N>0）。
- [ ] **API 可见**：启动后端后 `curl 'http://localhost:8000/api/content?source_type=x&limit=5'` 返回含 last30days 条目的 JSON。
- [ ] **前端可搜**：打开 `/search`，出现 Reddit/X/Hacker News 等筛选 chip，点击可过滤。
- [ ] **简报隔离**：`./venv/bin/python -m pytest tests/ -q` 全绿，且新 source_type 不进简报（`grep FEED_SOURCE_TYPES backend/services/briefing_generator.py` 不含 reddit/x/hn 等）。
- [ ] **端到端（可选，需 key）**：`./venv/bin/python cli.py import-last30days --topic "Loop Engineering"`。

---

## Self-Review 记录

- **Spec 覆盖**：L1 解析器(Task2)、文件/目录导入(Task3)、L2 wingsbot import 触发(Task4)、L3 CLI(Task5)、前端 chip(Task6)、技能安装(Task7)、wingsbot 可导入(Task1) —— spec 各节均有对应任务。
- **占位符**：无 TODO/TBD；每个代码步骤含完整代码。
- **类型/命名一致**：`parse_last30days_markdown` / `import_last30days_file` / `import_last30days_dir` / `run_last30days_via_wingsbot` / `_trigger_wingsbot` / `_newest_report_since` / `L30_OUTPUT_DIR` / `DEFAULT_L30_DIR` / `cmd_import_last30days` 在各任务间一致。
- **tags 取值**：plan 实现为 `[topic]`（spec 写的 `[topic, ...集群关键词]` 的最简确定性实现；集群标题保留在 `metadata.cluster_title`，如需关键词可后续增强）。
