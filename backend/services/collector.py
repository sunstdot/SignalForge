"""内容收集服务 - 主控逻辑"""
import asyncio
import json
import os
import re
import httpx
from datetime import datetime, timedelta
from typing import List, Dict
import yaml

from .storage import store_content_items, get_all_dates, _load_content_file, _save_content_file
from .rss_fetcher import fetch_rss_feeds
from .arxiv_fetcher import fetch_arxiv_papers
from .github_fetcher import fetch_github_trending
from .models_fetcher import fetch_model_platforms
from .anthropic_blog_fetcher import fetch_anthropic_technical_articles, normalize_url
from .hn_top_fetcher import fetch_hn_top
from .subreddit_fetcher import fetch_subreddits
from .source_run_store import save_source_run
from .event_radar import run_event_radar
from .x_account_daily import run_x_account_daily
from .company_blog import apply_company_blog_policy
from .watchlist_daily import run_watchlist_daily
from .chinese_briefer import generate_chinese_brief
from .llm_client import chat


async def run_collection(target_date: str = None):
    """运行数据收集，target_date 格式 YYYY-MM-DD，默认今日"""
    print("🚀 TokenBurner Collector starting...\n")

    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    config = load_config()
    print("✓ Configuration loaded")
    print(f"✓ Target date: {target_date}")

    # 并发抓取所有数据源
    print("\n📥 Fetching data from all sources...")
    all_items = await fetch_all_sources(config, target_date=target_date)
    print(f"\n✓ Total fetched: {len(all_items)} items")

    for item in all_items:
        item["created_at"] = target_date

    # 官方栏目页会连续两天包含同一篇新文，避免跨天重复推送。
    prior_ids = set()
    prior_social_ids = set()
    day = datetime.strptime(target_date, "%Y-%m-%d")
    for delta in (1, 2):
        previous = (day - timedelta(days=delta)).strftime("%Y-%m-%d")
        for old in _load_content_file(previous):
            if old.get("source_type") == "anthropic_blog":
                prior_ids.add(old.get("id"))
            if old.get("source_type") in {"hn", "reddit"}:
                prior_social_ids.add(old.get("id"))
    all_items = [
        item for item in all_items
        if (item.get("source_type") != "anthropic_blog" or item.get("id") not in prior_ids)
        and (item.get("source_type") not in {"hn", "reddit"} or item.get("id") not in prior_social_ids)
    ]

    # 公司博客分桶与折叠：保留所有原始条目
    all_items = apply_company_blog_policy(all_items)

    # 存储到文件
    stored = store_content_items(all_items)
    print(f"✓ Stored {stored} new items")

    account_config = config.get("sources", {}).get("x_public_accounts", {})
    if account_config.get("enabled") and target_date == datetime.now().strftime("%Y-%m-%d"):
        try:
            accounts = await run_x_account_daily(
                target_date, account_config.get("handles", []),
                max_posts_per_account=account_config.get("max_posts_per_account", 5),
                lookback_days=account_config.get("lookback_days", 2),
            )
            stored += accounts.get("stored_count", 0)
        except Exception as exc:
            # A blocked public profile must not erase official RSS/HN content.
            print(f"  ✗ X public account collection unavailable: {type(exc).__name__}")

    watchlist = config.get("sources", {}).get("watchlist", {})
    # 历史回填不触发昂贵的实时搜索，也不把旧帖伪装成当日新消息。
    if watchlist.get("enabled") and target_date == datetime.now().strftime("%Y-%m-%d"):
        print("\n📡 Running last30days watchlist...")
        accounts = [f"@{handle.lstrip('@')}" for handle in watchlist.get("accounts", [])
                    if isinstance(handle, str) and re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle.lstrip('@'))]
        topics = list(dict.fromkeys(watchlist.get("topics", []) + accounts))
        stored += await asyncio.to_thread(run_watchlist_daily, topics, target_date)

    print("\n🎉 Collection completed!")
    return stored


async def run_daily(date: str):
    """一键运行：收集 → 批量生成速读摘要"""
    print(f"📅 Running daily pipeline for {date}\n")

    print("=" * 50)
    print("Step 1/2: 数据收集")
    print("=" * 50)
    await run_collection(target_date=date)

    print("\n" + "=" * 50)
    print("Step 2/2: 批量生成速读摘要")
    print("=" * 50)
    _run_batch_quick_reads(date)

    # 历史回填与简报 GET 不启动实时查证或额外模型调用。
    if date == datetime.now().strftime('%Y-%m-%d'):
        await run_event_radar(date)

    # 统计
    print("\n" + "=" * 50)
    print("📊 Summary")
    print("=" * 50)
    final_items = _load_content_file(date)
    by_type: Dict[str, int] = {}
    for item in final_items:
        t = item.get("source_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    print(f"  Today's items: {len(final_items)}")
    for t, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {t:15} {cnt:>4}")
    print(f"\n✅ Daily pipeline completed for {date}!")


def _run_batch_quick_reads(date: str):
    """批量为有摘要的条目生成速读缓存"""
    import re as _re, json as _json
    from .storage import load_quick_reads, save_quick_read

    items = _load_content_file(date)
    if not items:
        print("⚠️  No items found, skipping quick-reads")
        return

    cached = load_quick_reads(date)
    # 有 summary 或 original_content 可用，且未缓存
    to_process = [
        i for i in items
        if (i.get("summary") or i.get("original_content"))
        and i["id"] not in cached
        and i.get("content_bucket") != "corporate"
        and not i.get("dup_of")
    ]

    # 新公开社区/热榜会一次带回大量帖子；已有信源的速读额度不受影响。
    social_origins = {"hn_top", "reddit_subreddit", "x_public_account"}
    # Always leave room for directly followed accounts, even after a large HN list.
    to_process.sort(key=lambda item: 0 if (item.get("metadata") or {}).get("origin") == "x_public_account" else 1)
    social_count = 0
    bounded = []
    for item in to_process:
        if (item.get("metadata") or {}).get("origin") in social_origins:
            if social_count >= 20:
                continue
            social_count += 1
        bounded.append(item)
    to_process = bounded

    if not to_process:
        print(f"✅ All {len(cached)} items already cached")
        return

    print(f"  Processing {len(to_process)} items ({len(cached)} already cached)...")

    BATCH_SIZE = 15
    generated = 0

    for batch_start in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[batch_start:batch_start + BATCH_SIZE]
        print(f"  Batch {batch_start // BATCH_SIZE + 1}: {len(batch)} items...", end=" ", flush=True)

        items_text = "\n".join(
            f"[{idx}] 标题：{item['title']}\n    摘要：{(item.get('summary') or item.get('original_content') or '')[:500]}"
            for idx, item in enumerate(batch, 1)
        )

        prompt = f"""以下是 {len(batch)} 篇文章的标题和摘要，请对每篇生成速读总结，输出 JSON 数组（只输出 JSON，不要 markdown 代码块）。

{items_text}

输出格式（每个字段都是单行字符串，不含换行符）：
[
  {{
    "idx": 1,
    "core": "核心内容：2-3句话概括文章",
    "points": ["要点一", "要点二", "要点三"],
    "insight": "最有价值的一个洞察（1句话）"
  }}
]

要求：中文输出，core 和 insight 为单行字符串，points 为字符串数组（3-5条）。"""

        try:
            raw = chat([{"role": "user", "content": prompt}]).strip()
            raw = _re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
            match = _re.search(r'\[.*\]', raw, _re.DOTALL)
            results = _json.loads(match.group(0) if match else raw)

            for r in results:
                real_idx = batch_start + r["idx"] - 1
                if real_idx < len(to_process):
                    item = to_process[real_idx]
                    points_md = "\n".join(f"- {p}" for p in (r.get("points") or []))
                    summary = f"**核心内容**：{r.get('core', '')}\n\n**关键信息**：\n{points_md}\n\n**值得关注**：{r.get('insight', '')}"
                    save_quick_read(date, item["id"], summary)
                    generated += 1
            print(f"✓ {len(results)} generated")
        except Exception as e:
            print(f"✗ failed: {e}")

    print(f"  ✅ {generated} quick-reads generated")


def _build_chinese_markdown(date: str, items: List[Dict]) -> str:
    """将带中文字段的 items 构建成 Markdown 简报"""
    type_labels = {
        "paper": "📄 学术论文",
        "arxiv": "📄 arXiv 论文",
        "repo": "⭐ GitHub 热门",
        "github": "⭐ GitHub 热门",
        "model": "🤖 AI 模型",
        "rss": "📰 技术博客与资讯",
        "news": "📰 新闻动态",
        "newsletter": "📬 Newsletter",
        "smolai": "🤖 Smol AI 资讯",
    }

    lines = [
        f"# {date} AI 技术日报 (中文版)",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"> 共 {len(items)} 条资讯",
        "",
        "---",
        "",
    ]

    # 按 source_type 分组
    groups: Dict[str, list] = {}
    for item in items:
        st = item.get("source_type", "other")
        groups.setdefault(st, []).append(item)

    for source_type, group_items in groups.items():
        label = type_labels.get(source_type, f"📌 {source_type}")
        lines.append(f"## {label}")
        lines.append("")

        for idx, item in enumerate(group_items, 1):
            chinese_title = item.get("chinese_title", item.get("title", ""))
            original_title = item.get("title", "")
            url = item.get("url", "")
            source = item.get("source", "")
            chinese_summary = item.get("chinese_summary", "")
            chinese_insights = item.get("chinese_insights", [])
            key_topics = item.get("key_topics", [])
            score = item.get("relevance_score", 0)

            lines.append(f"### {idx}. [{chinese_title}]({url})")
            lines.append("")
            lines.append(f"**来源:** {source} | **相关性:** {score:.1f}/10")
            lines.append("")

            if original_title != chinese_title:
                lines.append(f"*原标题: {original_title}*")
                lines.append("")

            if chinese_summary:
                lines.append("**摘要:**  ")
                lines.append(chinese_summary)
                lines.append("")

            if chinese_insights:
                lines.append("**关键洞察:**")
                for insight in chinese_insights:
                    lines.append(f"- {insight}")
                lines.append("")

            if key_topics:
                tags = " ".join([f"`{t}`" for t in key_topics])
                lines.append(f"**标签:** {tags}")
                lines.append("")

            lines.append("---")
            lines.append("")

    return "\n".join(lines)


async def fetch_all_sources(config: Dict, target_date: str = None) -> List[Dict]:
    """并发抓取所有数据源"""
    sources_config = config.get("sources", {})
    tasks = []

    if sources_config.get("arxiv", {}).get("enabled"):
        tasks.append(("arXiv", fetch_arxiv_papers(sources_config["arxiv"])))

    if sources_config.get("github", {}).get("enabled"):
        tasks.append(("GitHub", fetch_github_trending(sources_config["github"])))

    if sources_config.get("models", {}).get("enabled"):
        tasks.append(("Models", fetch_model_platforms(sources_config["models"])))

    if sources_config.get("rss", {}).get("enabled"):
        tasks.append(("RSS", fetch_rss_feeds(sources_config["rss"], target_date=target_date)))

    tasks.append(("Anthropic Blog", fetch_anthropic_technical_articles(target_date=target_date)))

    all_items = []
    results = await asyncio.gather(
        *[coro for _, coro in tasks],
        return_exceptions=True
    )

    seen_urls = {}
    for (name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            print(f"  ✗ {name} failed: {result}")
        elif isinstance(result, list):
            # 策展内容统一设置高相关度分数
            for item in result:
                if item.get("relevance_score", 0) == 0:
                    item["relevance_score"] = 8
            accepted = 0
            for item in result:
                normalized_url = normalize_url(str(item.get("url", "")))
                if name == "Anthropic Blog" and normalized_url in seen_urls:
                    # 保留 RSS 兜底，但同一篇文章优先用核验过正文的官方直抓版本。
                    all_items[seen_urls[normalized_url]] = item
                    accepted += 1
                    continue
                if normalized_url:
                    seen_urls.setdefault(normalized_url, len(all_items))
                all_items.append(item)
                accepted += 1
            print(f"  ✓ {name}: {accepted} items")
        else:
            print(f"  ✗ {name}: unexpected result")

    # 历史回填仍保留原采集器，但不去实时追踪过去日期的社交热榜。
    if target_date == datetime.now().strftime("%Y-%m-%d"):
        discovery = sources_config.get("hn_top", {})
        communities = sources_config.get("reddit_communities", {})
        jobs = []
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            if discovery.get("enabled"):
                jobs.append(("hn", fetch_hn_top(client, target_date, limit=discovery.get("limit", 20))))
            if communities.get("enabled"):
                jobs.append(("reddit", fetch_subreddits(
                    client, target_date, communities.get("names", []),
                    max_per_sub=communities.get("max_per_sub", 3),
                )))
            results = await asyncio.gather(*(task for _, task in jobs), return_exceptions=True)
        if jobs:
            status = {"errors": {}}
            if discovery.get("enabled"):
                status["hn"] = "unavailable"
            if communities.get("enabled"):
                status["reddit"] = {}
            for (source, _), result in zip(jobs, results):
                if isinstance(result, Exception):
                    status["errors"][source] = type(result).__name__
                    if source == "reddit":
                        status["reddit"] = {
                            f"r/{name}": "unavailable" for name in communities.get("names", [])
                        }
                    continue
                all_items.extend(result["items"])
                if source == "hn":
                    status["hn"] = result["status"]
                else:
                    status["reddit"] = result["statuses"]
                    status["errors"].update(result.get("errors", {}))
            save_source_run(target_date, status)

    return all_items


def load_config() -> Dict:
    """加载配置文件"""
    config_paths = [
        "config/collector.yaml",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "collector.yaml"),
    ]

    for path in config_paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                return yaml.safe_load(f)

    return {
        "sources": {
            "arxiv": {"enabled": True, "categories": ["cs.AI"], "maxResults": 10},
            "github": {"enabled": True, "languages": ["any"], "timeRange": "daily"},
            "models": {"enabled": True, "platforms": []},
            "rss": {"enabled": True, "subscriptions": []}
        },
    }
