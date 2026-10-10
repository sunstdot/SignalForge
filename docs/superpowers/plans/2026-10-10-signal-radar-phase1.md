# SignalForge 双轨信号雷达 Phase 1 实施计划

**实施状态：** Phase 1 代码已落地；下方各 Task 的原始代码块保留为实施前草案，实际接口与测试以仓库当前文件及「执行修订」为准。真实 X 抓取依赖本地服务，尚未付费触发验证。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让每日流水线接入一手/高权威信号（Anthropic 技术文章确定性抓取、公司博客三桶分类去重、last30days watchlist 每日推送），并输出"灵感/执行"双轨今日信号。

**Architecture:** 复用现有 FastAPI + 文件型 JSON 存储 + `collector.py` 采集编排。Phase 1 不引入打分/聚类（那是 Phase 2），只做四件事：① Anthropic 抓取从 agent 改为确定性 HTTP；② 公司博客三桶分类 + 跨博客去重；③ last30days watchlist 每日接入；④ 简报生成器输出双轨 top-N。所有改动向后兼容，不删除任何数据源；Anthropic 原 RSS 保留为直抓失效时的兜底。

**Tech Stack:** Python 3.11+, FastAPI, aiohttp, pytest + pytest-asyncio。

**Spec:** `docs/superpowers/specs/2026-10-10-signal-radar-design.md`

## Global Constraints

- 测试运行：`cd backend && source venv/bin/activate && python -m pytest tests/<file>.py -v`
- 新测试放在 `backend/tests/`，用 `from backend.services import <module>` 导入。
- 不删除 `collector.yaml` 中任何数据源，Anthropic RSS 保留为兜底；直抓成功时同 URL 优先直抓。
- 新字段统一用 `content_bucket`（取值 `technical` / `product_launch` / `corporate`）；`signal` 打分对象留到 Phase 2。
- 代码注释与 docstring 用中文。
- 每个 Task 结束时 `python -m pytest tests/ -q` 全量通过再提交。

---

## 执行修订（用户批准后于 2026-10-10 实施）

- 计划中的 Anthropic RSS 删除步骤不执行：保留原 RSS，直抓成功则优先使用直抓正文；拉取失败保留 RSS。
- 原计划 `/research` HTML 解析假设不成立（真实页面的时间标签无 `dateTime`）；分别解析 Engineering 和 Research 实际页面，仅采近期并获取正文。
- 每日上游导入保留原发表时间、只纳入明确有发表日期的近期内容，成功话题当日不重复运行；配置支持关键词及可选 X 账号。
- 今日信号总量上限 15 条（非每轨 15 条）；已接入简报 API、网站首页和现有静态快照流程，而非仅增加未调用函数。
- 自动化不执行昂贵的四话题真实搜索，以免触发额外 API/模型费用；功能测试用假报告，官方 Anthropic 网页另做只读验证。

---

### Task 1: Anthropic 确定性抓取器（替换 wingsbot agent）

**Files:**
- Modify: `backend/services/anthropic_blog_fetcher.py`（整体重写）
- Test: `backend/tests/test_anthropic_blog_fetcher.py`（整体重写）
- Keep: `backend/config/collector.yaml:94-100` 中 `Anthropic Blog` rsshub 条目作为直抓失败兜底

**Interfaces:**
- Consumes: 无（本任务独立）。
- Produces:
  - `parse_anthropic_articles(html: str) -> List[Dict]` —— 纯函数，输入栏目页 HTML，输出 `[{"title","url","published_at","section"}]`，按日期降序。
  - `fetch_anthropic_technical_articles(target_date: str | None = None) -> List[Dict]`（async）—— 保持现有签名，`collector.py` 已 `from .anthropic_blog_fetcher import fetch_anthropic_technical_articles, normalize_url`，签名不可变。
  - `normalize_url(url: str) -> str` —— 保留现有实现，`collector.py` 依赖它。

- [ ] **Step 1: 写失败测试**

重写 `backend/tests/test_anthropic_blog_fetcher.py`：

```python
import pytest

from backend.services import anthropic_blog_fetcher as fetcher

FIXTURE_HTML = """
<html><body>
<article class="x">
  <a class="cardLink" href="/engineering/building-effective-agents">
    <img alt="Building effective agents" src="x.svg"/>
    <div class="content"><h3 class="headline-4">Building effective agents</h3>
    <div class="date"><time dateTime="2025-01-06">Jan 06, 2025</time></div></div>
  </a>
</article>
<article class="x">
  <a class="cardLink" href="/research/older-paper">
    <div class="content"><h3 class="headline-4">An older research paper</h3>
    <div class="date"><time dateTime="2024-12-01">Dec 01, 2024</time></div></div>
  </a>
</article>
<article class="x">
  <a class="cardLink" href="/news/company-announcement">
    <div class="content"><h3 class="headline-4">Anthropic welcomes new partner</h3>
    <div class="date"><time dateTime="2025-01-07">Jan 07, 2025</time></div></div>
  </a>
</article>
</body></html>
"""


def test_parse_anthropic_articles_extracts_and_sorts():
    articles = fetcher.parse_anthropic_articles(FIXTURE_HTML)
    assert [a["title"] for a in articles] == [
        "Building effective agents",
        "An older research paper",
    ]
    assert articles[0]["url"] == "https://www.anthropic.com/engineering/building-effective-agents"
    assert articles[0]["published_at"] == "2025-01-06"
    assert articles[0]["section"] == "engineering"
    assert articles[1]["section"] == "research"


@pytest.mark.asyncio
async def test_fetch_returns_deduped_items(monkeypatch):
    async def fake_fetch(url):
        return FIXTURE_HTML

    monkeypatch.setattr(fetcher, "_fetch_html", fake_fetch)
    items = await fetcher.fetch_anthropic_technical_articles("2025-01-07")
    titles = [i["title"] for i in items]
    assert titles == ["Building effective agents", "An older research paper"]
    assert all(i["source_type"] == "anthropic_blog" for i in items)
    assert all(i["source"] == "Anthropic" for i in items)
    assert items[0]["relevance_score"] == 8


@pytest.mark.asyncio
async def test_fetch_swallows_errors(monkeypatch):
    async def fake_fetch(url):
        raise RuntimeError("boom")

    monkeypatch.setattr(fetcher, "_fetch_html", fake_fetch)
    items = await fetcher.fetch_anthropic_technical_articles("2025-01-07")
    assert items == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_anthropic_blog_fetcher.py -v`
Expected: FAIL（`parse_anthropic_articles`、`_fetch_html` 不存在；旧的 wingsbot mock 测试已被覆盖）。

- [ ] **Step 3: 重写 fetcher**

整体重写 `backend/services/anthropic_blog_fetcher.py`：

```python
"""Anthropic engineering / research 技术文章确定性抓取。

替代旧的 wingsbot-agent 方案：直接 HTTP 抓取栏目页（服务端渲染 HTML），
解析出文章标题、链接、日期，不依赖外部 agent。
"""
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import aiohttp

BASE_URL = "https://www.anthropic.com"
SECTIONS = ("engineering", "research")
MAX_ITEMS_PER_SECTION = 5

_ARTICLE_BLOCK_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.DOTALL)
_LINK_RE = re.compile(r'href="(/[^"]+)"')
_TITLE_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.DOTALL)
_DATE_RE = re.compile(r'<time[^>]*dateTime="([^"]+)"')
_TAG_RE = re.compile(r"<[^>]+>")


def normalize_url(url: str) -> str:
    """Return a stable URL suitable for cross-source deduplication."""
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return ""
    if not host:
        return ""
    if port:
        host = f"{host}:{port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, "", ""))


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def parse_anthropic_articles(html: str) -> List[Dict]:
    """从栏目页 HTML 提取文章，返回按日期降序、去重后的列表。"""
    articles: List[Dict] = []
    for block in _ARTICLE_BLOCK_RE.findall(html):
        link_m = _LINK_RE.search(block)
        title_m = _TITLE_RE.search(block)
        date_m = _DATE_RE.search(block)
        if not (link_m and title_m and date_m):
            continue
        path = link_m.group(1)
        if "/engineering/" in path:
            section = "engineering"
        elif "/research/" in path:
            section = "research"
        else:
            continue
        title = _clean(title_m.group(1))
        date = date_m.group(1)[:10]
        if not title or not date:
            continue
        articles.append({
            "title": title,
            "url": BASE_URL + path,
            "published_at": date,
            "section": section,
        })

    seen: set = set()
    out: List[Dict] = []
    for a in sorted(articles, key=lambda x: x["published_at"], reverse=True):
        if a["url"] in seen:
            continue
        seen.add(a["url"])
        out.append(a)
    return out


def _article_to_item(article: Dict, target_date: Optional[str]) -> Dict:
    canonical_url = normalize_url(article["url"])
    item_id = "anthropic-" + hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:20]
    return {
        "id": item_id,
        "title": article["title"],
        "url": canonical_url,
        "source": "Anthropic",
        "source_type": "anthropic_blog",
        "summary": "",
        "published_at": article["published_at"],
        "created_at": target_date or datetime.now().strftime("%Y-%m-%d"),
        "category": [article["section"].capitalize()],
        "tags": ["anthropic", article["section"]],
        "relevance_score": 8,
    }


async def _fetch_html(url: str) -> str:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SignalForge/1.0)"},
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            return await response.text()


async def fetch_anthropic_technical_articles(target_date: Optional[str] = None) -> List[Dict]:
    """抓取 Anthropic engineering + research 最新技术文章，失败不抛异常。"""
    items: List[Dict] = []
    for section in SECTIONS:
        try:
            html = await _fetch_html(f"{BASE_URL}/{section}")
            articles = parse_anthropic_articles(html)[:MAX_ITEMS_PER_SECTION]
            for article in articles:
                items.append(_article_to_item(article, target_date))
            print(f"  ✓ Anthropic {section}: {len(articles)} items")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Anthropic {section} failed: {exc}")

    seen: set = set()
    deduped: List[Dict] = []
    for item in items:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        deduped.append(item)
    return deduped
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_anthropic_blog_fetcher.py -v`
Expected: PASS（3 个测试全绿）。

- [ ] **Step 5: 保留 rsshub 兜底**

按「执行修订」保留 `Anthropic Blog` rsshub 订阅；在 `fetch_all_sources` 里仅当官方直抓成功时以直抓版本覆盖同 URL RSS 条目。

- [ ] **Step 6: 全量测试 + 提交**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/ -q`
Expected: PASS。

```bash
git add backend/services/anthropic_blog_fetcher.py backend/tests/test_anthropic_blog_fetcher.py backend/config/collector.yaml
git commit -m "feat: Anthropic 技术文章改为确定性 HTML 抓取，替换 wingsbot agent"
```

---

### Task 2: 公司博客三桶分类 + 跨博客去重

**Files:**
- Create: `backend/services/company_blog.py`
- Test: `backend/tests/test_company_blog.py`
- Modify: `backend/services/collector.py`（在 `run_collection` 里对采集结果应用策略）

**Interfaces:**
- Consumes: 采集产出的 item dict（含 `id/source/source_type/title/relevance_score`）。
- Produces:
  - `classify_company_blog(item: Dict) -> str` —— 返回 `"technical" | "product_launch" | "corporate"`。
  - `dedup_company_blogs(items: List[Dict]) -> List[Dict]` —— 标题 token 重叠率 > 0.6 视为重复，保留首篇，其余加 `dup_of` 字段。
  - `apply_company_blog_policy(items: List[Dict]) -> List[Dict]` —— 对全量 items 打 `content_bucket` 标签；corporate 减 4 分（下限 0），product_launch 加 2 分。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_company_blog.py`：

```python
from backend.services import company_blog


def test_classify_corporate_pr_titles():
    assert company_blog.classify_company_blog(
        {"source_type": "blog", "title": "Grab and OpenAI bring practical AI skills to Southeast Asia"}
    ) == "corporate"
    assert company_blog.classify_company_blog(
        {"source_type": "blog", "title": "New experts join Google's AI & Economy team"}
    ) == "corporate"


def test_classify_product_launch():
    assert company_blog.classify_company_blog(
        {"source_type": "blog", "title": "Introducing Gemini 3.8 Live"}
    ) == "product_launch"


def test_classify_technical_default():
    assert company_blog.classify_company_blog(
        {"source_type": "blog", "title": "Better prompt caching for GPT-6"}
    ) == "technical"
    assert company_blog.classify_company_blog(
        {"source_type": "blog", "title": "Open-Sourcing Rebalancer"}
    ) == "technical"


def test_anthropic_blog_always_technical():
    assert company_blog.classify_company_blog(
        {"source_type": "anthropic_blog", "title": "Introducing Claude Code"}
    ) == "technical"


def test_dedup_marks_duplicates():
    items = [
        {"id": "a", "title": "Introducing Gemini 3.8 Live", "source": "Google DeepMind Blog"},
        {"id": "b", "title": "Gemini 3.8 Live is now available", "source": "Google AI Blog"},
        {"id": "c", "title": "Open-Sourcing Rebalancer", "source": "Meta Engineering"},
    ]
    out = company_blog.dedup_company_blogs(items)
    assert "dup_of" not in out[0]
    assert out[1]["dup_of"] == "a"
    assert "dup_of" not in out[2]


def test_apply_policy_demotes_corporate_and_boosts_launch():
    items = [
        {"id": "a", "source": "OpenAI Blog", "source_type": "blog",
         "title": "Grab and OpenAI bring practical AI skills", "relevance_score": 8},
        {"id": "b", "source": "Google DeepMind Blog", "source_type": "blog",
         "title": "Introducing Gemini 3.8 Live", "relevance_score": 8},
    ]
    out = company_blog.apply_company_blog_policy(items)
    by_id = {i["id"]: i for i in out}
    assert by_id["a"]["content_bucket"] == "corporate"
    assert by_id["a"]["relevance_score"] == 4
    assert by_id["b"]["content_bucket"] == "product_launch"
    assert by_id["b"]["relevance_score"] == 10
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_company_blog.py -v`
Expected: FAIL（`company_blog` 模块不存在）。

- [ ] **Step 3: 实现 company_blog 模块**

创建 `backend/services/company_blog.py`：

```python
"""公司博客内容策略：三桶分类 + 跨博客去重。"""
import re
from typing import Dict, List

COMPANY_BLOG_SOURCES = {
    "OpenAI Blog", "Google DeepMind Blog", "Google AI Blog",
    "Meta Engineering", "Anthropic Blog", "Cohere Blog",
    "Mistral Blog", "Microsoft AI Blog", "xAI Blog",
}

# 公司新闻/PR 关键词（优先判断，强负面信号）
CORPORATE_KEYWORDS = [
    "partnership", "partners with", "collaborat", "funding", "raises ",
    "welcome", "joins ", "join ", "hiring", "experts", "policy",
    "cyber", "defense", "nonprofit", "grant", "award", "co-creating",
    "fashion", "economy", "workforce", "education", "for civilian",
    "skills to", "new experts",
]

# 产品/模型发布关键词（发布动词，避免模型名误伤技术文章）
PRODUCT_KEYWORDS = [
    "introducing", "launch", "announcing", "now available",
    "release", "shipping", "new model",
]


def classify_company_blog(item: Dict) -> str:
    """返回 'technical' | 'product_launch' | 'corporate'。"""
    if item.get("source_type") == "anthropic_blog":
        return "technical"
    title = (item.get("title") or "").lower()
    for kw in CORPORATE_KEYWORDS:
        if kw in title:
            return "corporate"
    for kw in PRODUCT_KEYWORDS:
        if kw in title:
            return "product_launch"
    return "technical"


def _title_tokens(title: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (title or "").lower()))


def dedup_company_blogs(items: List[Dict]) -> List[Dict]:
    """标题 token 重叠率 > 0.6 视为同一条，保留首篇，其余标 dup_of。"""
    kept: List[Dict] = []
    for item in items:
        tokens = _title_tokens(item.get("title", ""))
        dup = None
        if tokens:
            for k in kept:
                if k.get("dup_of"):
                    continue
                kt = _title_tokens(k.get("title", ""))
                if not kt:
                    continue
                overlap = len(tokens & kt) / min(len(tokens), len(kt))
                if overlap > 0.6:
                    dup = k["id"]
                    break
        if dup:
            item["dup_of"] = dup
        kept.append(item)
    return kept


def apply_company_blog_policy(items: List[Dict]) -> List[Dict]:
    """对公司博客条目做三桶分类 + 去重 + 分值调整，原地更新并返回。"""
    company_items = [
        i for i in items
        if i.get("source") in COMPANY_BLOG_SOURCES
        or i.get("source_type") == "anthropic_blog"
    ]
    dedup_company_blogs(company_items)
    for item in company_items:
        bucket = classify_company_blog(item)
        item["content_bucket"] = bucket
        if bucket == "corporate":
            item["relevance_score"] = max(0, item.get("relevance_score", 0) - 4)
        elif bucket == "product_launch":
            item["relevance_score"] = item.get("relevance_score", 0) + 2
    return items
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_company_blog.py -v`
Expected: PASS。

- [ ] **Step 5: 接入 collector**

编辑 `backend/services/collector.py`。在文件顶部 import 区加入：

```python
from .company_blog import apply_company_blog_policy
```

在 `run_collection` 中，找到：

```python
    for item in all_items:
        item["created_at"] = target_date

    # 存储到文件
    stored = store_content_items(all_items)
```

改为：

```python
    for item in all_items:
        item["created_at"] = target_date

    # 公司博客三桶分类 + 跨博客去重
    all_items = apply_company_blog_policy(all_items)

    # 存储到文件
    stored = store_content_items(all_items)
```

- [ ] **Step 6: 全量测试 + 提交**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/ -q`
Expected: PASS。

```bash
git add backend/services/company_blog.py backend/tests/test_company_blog.py backend/services/collector.py
git commit -m "feat: 公司博客三桶分类与跨博客去重，PR 内容降权"
```

---

### Task 3: last30days watchlist 每日接入

**Files:**
- Create: `backend/services/watchlist_daily.py`
- Test: `backend/tests/test_watchlist_daily.py`
- Modify: `backend/config/collector.yaml`（新增 `watchlist` 配置段）
- Modify: `backend/services/collector.py`（`run_collection` 末尾触发 watchlist）

**Interfaces:**
- Consumes: `run_last30days_via_wingsbot(topic: str) -> int`（`backend/services/last30days_importer.py` 已有，返回新增条数）。
- Produces: `run_watchlist_daily(topics: List[str]) -> int` —— 逐 topic 触发并导入，返回总条数；单个失败不阻断。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_watchlist_daily.py`：

```python
from backend.services import watchlist_daily


def test_run_watchlist_daily_calls_importer_for_each_topic(monkeypatch):
    calls = []

    def fake_run(topic):
        calls.append(topic)
        return 5

    monkeypatch.setattr(watchlist_daily, "run_last30days_via_wingsbot", fake_run)
    total = watchlist_daily.run_watchlist_daily(["AI agent", "vibe coding"])
    assert calls == ["AI agent", "vibe coding"]
    assert total == 10


def test_run_watchlist_daily_swallows_errors(monkeypatch):
    calls = []

    def fake_run(topic):
        calls.append(topic)
        if topic == "bad":
            raise RuntimeError("boom")
        return 3

    monkeypatch.setattr(watchlist_daily, "run_last30days_via_wingsbot", fake_run)
    total = watchlist_daily.run_watchlist_daily(["bad", "good"])
    assert calls == ["bad", "good"]
    assert total == 3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_watchlist_daily.py -v`
Expected: FAIL（`watchlist_daily` 模块不存在）。

- [ ] **Step 3: 实现 watchlist_daily 模块**

创建 `backend/services/watchlist_daily.py`：

```python
"""把 last30days watchlist 接入每日采集流水线。"""
from typing import List

from .last30days_importer import run_last30days_via_wingsbot


def run_watchlist_daily(topics: List[str]) -> int:
    """逐 topic 触发 last30days 研究并导入，返回新增总条数；单个失败不阻断。"""
    total = 0
    for topic in topics:
        try:
            n = run_last30days_via_wingsbot(topic)
            total += n
            print(f"  ✓ watchlist '{topic}': {n} items")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ watchlist '{topic}' failed: {exc}")
    return total
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_watchlist_daily.py -v`
Expected: PASS。

- [ ] **Step 5: 新增 watchlist 配置**

编辑 `backend/config/collector.yaml`，在 `sources:` 下的 `rss:` 段之后新增（与 `arxiv:`、`github:` 同级缩进）：

```yaml
  # ============================================================
  # 五、last30days watchlist（一手信号每日推送）
  # ============================================================
  watchlist:
    enabled: true
    topics:
      - "AI agent"
      - "vibe coding"
      - "RAG"
      - "LLM new model"
```

- [ ] **Step 6: 接入 collector**

编辑 `backend/services/collector.py`，在 `run_collection` 中，找到：

```python
    # 存储到文件
    stored = store_content_items(all_items)
    print(f"✓ Stored {stored} new items")

    print("\n🎉 Collection completed!")
    return stored
```

改为：

```python
    # 存储到文件
    stored = store_content_items(all_items)
    print(f"✓ Stored {stored} new items")

    # last30days watchlist：一手信号每日推送（在独立线程跑，避免事件循环冲突）
    watchlist_cfg = config.get("sources", {}).get("watchlist", {})
    if watchlist_cfg.get("enabled"):
        print("\n📡 Running last30days watchlist...")
        from .watchlist_daily import run_watchlist_daily
        n = await asyncio.to_thread(run_watchlist_daily, watchlist_cfg.get("topics", []))
        print(f"✓ watchlist imported {n} items")

    print("\n🎉 Collection completed!")
    return stored
```

- [ ] **Step 7: 全量测试 + 提交**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/ -q`
Expected: PASS。

```bash
git add backend/services/watchlist_daily.py backend/tests/test_watchlist_daily.py backend/config/collector.yaml backend/services/collector.py
git commit -m "feat: last30days watchlist 接入每日采集流水线"
```

---

### Task 4: 双轨今日信号输出

**Files:**
- Modify: `backend/services/briefing_generator.py`（新增双轨函数）
- Test: `backend/tests/test_signal_feed.py`

**Interfaces:**
- Consumes: `_load_content_file(date) -> List[Dict]`（`briefing_generator.py` 已从 storage 导入）。
- 实际产物：`build_signal_feed(items, quick_reads, limit=15)`（`backend/services/signal_feed.py`），总计最多 15 条，简报 API 的 `signals` 字段与网站首页消费它。下方为原计划草案。
- 说明：Phase 1 的 "so-what 一句" 复用现有 quick-read 的 `insight` 字段（`_run_batch_quick_reads` 已生成），本任务不新增 LLM 调用；完整 so-what 生成器留到 Phase 3。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_signal_feed.py`：

```python
from backend.services import briefing_generator


def _items():
    return [
        {"id": "1", "source_type": "repo", "title": "repo", "relevance_score": 8},
        {"id": "2", "source_type": "paper", "title": "paper", "relevance_score": 9},
        {"id": "3", "source_type": "x", "title": "tweet", "relevance_score": 7},
        {"id": "4", "source_type": "blog", "title": "corp", "relevance_score": 9, "content_bucket": "corporate"},
        {"id": "5", "source_type": "blog", "title": "launch", "relevance_score": 9, "content_bucket": "product_launch"},
        {"id": "6", "source_type": "blog", "title": "tech", "relevance_score": 6, "content_bucket": "technical"},
    ]


def test_signal_feed_splits_tracks_and_excludes_corporate(monkeypatch):
    monkeypatch.setattr(briefing_generator, "_load_content_file", lambda date: _items())
    feed = briefing_generator.generate_signal_feed("2026-10-10")
    insp_ids = {i["id"] for i in feed["inspiration"]}
    exec_ids = {i["id"] for i in feed["execution"]}
    assert insp_ids == {"3", "5"}
    assert exec_ids == {"1", "2", "6"}
    assert "4" not in insp_ids and "4" not in exec_ids


def test_signal_feed_sorts_desc_and_limits(monkeypatch):
    items = [
        {"id": str(i), "source_type": "repo", "title": f"r{i}", "relevance_score": i}
        for i in range(20)
    ]
    monkeypatch.setattr(briefing_generator, "_load_content_file", lambda date: items)
    feed = briefing_generator.generate_signal_feed("2026-10-10", top_n=5)
    assert [i["id"] for i in feed["execution"]] == ["19", "18", "17", "16", "15"]
    assert feed["inspiration"] == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_signal_feed.py -v`
Expected: FAIL（`generate_signal_feed` 不存在）。

- [ ] **Step 3: 实现双轨函数**

在 `backend/services/briefing_generator.py` 顶部常量区（`FEED_SOURCE_TYPES = ...` 之后）新增：

```python
EXECUTION_TYPES = {"paper", "arxiv", "repo", "github", "model", "anthropic_blog"}
INSPIRATION_TYPES = {"x", "reddit", "hn", "hackernews", "smolai", "news", "producthunt"}
```

在文件末尾新增：

```python
def _track_of(item: Dict) -> Optional[str]:
    """返回 'inspiration' / 'execution' / None（不进今日信号）。"""
    bucket = item.get("content_bucket")
    if bucket == "corporate":
        return None
    if bucket == "product_launch":
        return "inspiration"
    if bucket == "technical":
        return "execution"
    st = item.get("source_type")
    if st in EXECUTION_TYPES:
        return "execution"
    if st in INSPIRATION_TYPES:
        return "inspiration"
    return None


def generate_signal_feed(date: str, top_n: int = 15) -> Dict:
    """按灵感/执行双轨输出今日信号，每轨最多 top_n 条，按 relevance_score 降序。"""
    items = _load_content_file(date)
    feed: Dict = {"inspiration": [], "execution": []}
    for item in items:
        track = _track_of(item)
        if track:
            feed[track].append(item)
    for track in ("inspiration", "execution"):
        feed[track].sort(key=lambda x: -x.get("relevance_score", 0))
        feed[track] = feed[track][:top_n]
    return feed
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_signal_feed.py -v`
Expected: PASS。

- [ ] **Step 5: 全量测试 + 提交**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/ -q`
Expected: PASS。

```bash
git add backend/services/briefing_generator.py backend/tests/test_signal_feed.py
git commit -m "feat: 简报生成器输出灵感/执行双轨今日信号"
```

---

## 完成后的手工验证（不写测试，跑一遍真流水线）

```bash
cd backend && source venv/bin/activate
python -m pytest tests/ -q                 # 全绿
python cli.py collect --date $(date +%F)   # 观察：Anthropic 有 items、公司博客带 content_bucket、watchlist 有导入数
python cli.py daily $(date +%F)            # 观察：今日信号双轨输出正常
```

预期现象：

- 日志里出现 `✓ Anthropic engineering: N items` 与 `✓ Anthropic research: N items`。
- 日志里出现 `✓ watchlist 'AI agent': N items` 等。
- `data/content/` 当日 JSON 里，公司博客条目带 `content_bucket`，corporate 条目 `relevance_score` 被压低。
