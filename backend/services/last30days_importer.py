"""last30days raw v3 markdown → SignalForge content items."""
import asyncio
import hashlib
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from services.storage import store_content_items

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
_META_DATE_RE = re.compile(r"^\s*-\s*(\d{4}-\d{2}-\d{2})\b.*\|\s*score:")
_ITEM_SCORE_RE = re.compile(r"\|\s*score:\s*(\d+)")
_URL_RE = re.compile(r"^\s*-\s*URL:\s*(\S+)")
_EVIDENCE_RE = re.compile(r"^\s*-\s*Evidence:\s*(.+?)\s*$")


def _make_id(platform_key: str, url: str, title: str) -> str:
    basis = url or title
    return f"l30-{platform_key}-{hashlib.md5(basis.encode('utf-8')).hexdigest()[:12]}"


def _clean_author(a: str) -> str:
    """作者段：youtube 是 dict（取 handle / title），其余原样。"""
    a = a.strip()
    if a.startswith("{"):
        m = re.search(r"'handle':\s*'([^']*)'", a)
        if m and m.group(1):
            return "@" + m.group(1)
        m = re.search(r"'title':\s*'([^']*)'", a)
        return m.group(1) if m else ""
    return a


def _parse_meta_line(line: str) -> Dict:
    """解析 meta 行：'- <date> | <author> | [<engagement>] | score:N'。"""
    body = line.strip()
    if body.startswith("-"):
        body = body[1:].strip()
    segs = [s.strip() for s in body.split("|")]

    date = None
    if segs:
        dm = re.match(r"(\d{4}-\d{2}-\d{2})", segs[0])
        if dm:
            date = dm.group(1)

    score = None
    sm = _ITEM_SCORE_RE.search(line)
    if sm:
        score = int(sm.group(1))

    engagement = ""
    for s in segs:
        mb = re.fullmatch(r"\[(.+)\]", s)
        if mb and not mb.group(1).lower().startswith("date:"):
            engagement = mb.group(1)
            break

    author = ""
    for s in segs[1:]:
        if not s or s.startswith("[") or s.lower().startswith("score:"):
            continue
        author = s
        break
    author = _clean_author(author)

    volume = 0
    for n in re.findall(r"[\d,]+", engagement):
        try:
            volume += int(n.replace(",", ""))
        except ValueError:
            pass

    return {"date": date, "author": author, "engagement": engagement, "volume": volume, "score": score}


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
        # 优先用条目自身 score（每条 meta 行都有 | score:N），回退 cluster 分；约 0–60 → 0–10
        raw_score = cur.get("score", cluster_score)
        score = min(10, round(raw_score / 6))
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
                "author": cur.get("author", ""),
                "engagement": cur.get("engagement", ""),
                "volume": cur.get("volume", 0),
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
        if line.startswith("###"):
            flush()
            m = _CLUSTER_RE.match(line)
            if m:
                cluster_title, cluster_score = m.group(1), int(m.group(2))
            else:
                cluster_title, cluster_score = "", 0
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
        if "| score:" in line:
            meta = _parse_meta_line(line)
            if "date" not in cur and meta["date"]:
                cur["date"] = meta["date"]
            if "score" not in cur and meta["score"] is not None:
                cur["score"] = meta["score"]
            if "author" not in cur and meta["author"]:
                cur["author"] = meta["author"]
            if "engagement" not in cur and meta["engagement"]:
                cur["engagement"] = meta["engagement"]
                cur["volume"] = meta["volume"]
            continue

    flush()
    return items


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


_loop = None
_loop_lock = threading.Lock()


def _persistent_loop():
    """进程级常驻事件循环（独立线程）。

    wingsbot 走 litellm 调 LLM；litellm 会在事件循环上注册全局后台任务
    （LoggingWorker）和 httpx/aiohttp 连接池。若每次新建并关闭一个临时 loop，
    这些全局对象会绑死在已关闭的 loop 上，触发 'Event loop is closed' /
    'Task was destroyed but it is pending' / 'aclose(): asynchronous generator
    is already running' 等噪音。用一个永不关闭的常驻 loop 即可根治。
    """
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            threading.Thread(target=_loop.run_forever, daemon=True,
                             name="last30days-loop").start()
    return _loop


def _run_async(coro):
    """把协程提交到常驻事件循环并同步等待结果。"""
    return asyncio.run_coroutine_threadsafe(coro, _persistent_loop()).result()


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
    prompt = (
        f"使用 last30days 技能研究话题：{topic}。"
        f"完成后把原始结果（raw v3 markdown）保存到 {L30_OUTPUT_DIR}/。"
    )

    async def _run():
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
        try:
            return await agent_loop.process_direct(prompt, session_key="signalforge:last30days")
        finally:
            await agent_loop.close_mcp()

    response = _run_async(_run())
    md_path = _newest_report_since(start)
    if md_path is None:
        raise RuntimeError(
            "wingsbot 未产出 last30days 报告文件。agent 返回（节选）：\n"
            + (response or "")[:500]
        )
    return md_path
