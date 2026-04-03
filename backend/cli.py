#!/usr/bin/env python3
"""
TokenBurner CLI 工具
用于手动触发数据收集和简报生成
"""

import asyncio
import argparse
import json
import os
from datetime import datetime
import sys

from services.storage import get_content_stats, get_all_dates, _load_content_file
from services.collector import run_collection, run_daily, load_config


def cmd_daily(args):
    """一键运行：收集 → 生成简报"""
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    asyncio.run(run_daily(date))


def cmd_collect(args):
    """运行数据收集"""
    print("🚀 Starting data collection...")
    asyncio.run(run_collection())


def cmd_briefing(args):
    """生成简报（不重新收集数据）"""
    from services.briefing_generator import generate_briefing_for_date, get_briefing_markdown

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    print(f"📝 Generating briefing for {date}...")

    briefing = generate_briefing_for_date(date)

    if briefing:
        items_count = len(briefing.get("items", []))
        print(f"✅ Briefing generated with {items_count} items")

        # 保存 Markdown
        markdown = get_briefing_markdown(date)
        output_dir = os.path.join(os.path.dirname(__file__), "docs", "daily-briefings")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{date}.md")
        with open(output_path, "w") as f:
            f.write(markdown)
        print(f"✓ Saved to {output_path}")
    else:
        print("❌ No items found for briefing")


def cmd_stats(args):
    """显示统计信息"""
    stats = get_content_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    today_items = _load_content_file(today)

    # 按 source 统计
    by_name: dict = {}
    for item in _load_content_file(today):
        src = item.get("source", "unknown")
        by_name[src] = by_name.get(src, 0) + 1

    dates = get_all_dates()[:7]

    print("\n📊 TokenBurner Stats")
    print("=" * 50)
    print(f"Total items:       {stats['total']}")
    print(f"Today:             {stats['today']}")

    print("\nBy source type:")
    for t, cnt in sorted(stats['by_source'].items(), key=lambda x: -x[1]):
        print(f"  {t:20} {cnt:>5}")

    print("\nTop sources (today):")
    for src, cnt in sorted(by_name.items(), key=lambda x: -x[1])[:20]:
        print(f"  {src:30} {cnt:>5}")

    print("\nRecent dates:")
    for d in dates:
        count = len(_load_content_file(d))
        print(f"  {d}  {count:>4} items")
    print("=" * 50)


def cmd_refetch(args):
    """重新抓取指定日期的数据"""
    import json
    from pathlib import Path
    from services.storage import CONTENT_DIR, store_content_items
    from services.rss_fetcher import fetch_rss_feeds
    from services.arxiv_fetcher import fetch_arxiv_papers
    from services.github_fetcher import fetch_github_trending
    from services.models_fetcher import fetch_model_platforms

    date = args.date
    print(f"🔄 Refetching data for {date}...")

    config = load_config()

    # 删除旧数据文件
    old_file = CONTENT_DIR / f"{date}.json"
    if old_file.exists():
        old_file.unlink()
        print(f"✓ Deleted old data file for {date}")

    # 重新抓取
    async def fetch_for_date():
        items = []
        sources = config.get("sources", {})
        if sources.get("arxiv", {}).get("enabled"):
            items.extend(await fetch_arxiv_papers(sources["arxiv"]))
        if sources.get("github", {}).get("enabled"):
            items.extend(await fetch_github_trending(sources["github"]))
        if sources.get("models", {}).get("enabled"):
            items.extend(await fetch_model_platforms(sources["models"]))
        if sources.get("rss", {}).get("enabled"):
            items.extend(await fetch_rss_feeds(sources["rss"]))
        return items

    items = asyncio.run(fetch_for_date())
    print(f"✓ Fetched {len(items)} items")

    # 强制设定日期
    target_date = datetime.strptime(date, "%Y-%m-%d")
    for item in items:
        item["created_at"] = target_date
        if item.get("relevance_score", 0) == 0:
            item["relevance_score"] = 8

    stored = store_content_items(items)
    print(f"✓ Stored {stored} items")

    # 生成简报
    from services.briefing_generator import generate_briefing_for_date, get_briefing_markdown
    briefing = generate_briefing_for_date(date)
    if briefing:
        markdown = get_briefing_markdown(date)
        output_dir = os.path.join(os.path.dirname(__file__), "docs", "daily-briefings")
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, f"{date}.md"), "w") as f:
            f.write(markdown)
        print(f"✓ Briefing saved with {len(briefing['items'])} items")

    print("\n✅ Done!")


def main():
    parser = argparse.ArgumentParser(
        description="TokenBurner CLI - AI 情报收集工具",
        prog="tokenburner"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # daily - 一键完成
    daily_parser = subparsers.add_parser("daily", help="一键运行：收集 → 生成简报")
    daily_parser.add_argument("date", nargs="?", help="Date (YYYY-MM-DD), default today")
    daily_parser.set_defaults(func=cmd_daily)

    # collect - 只收集
    collect_parser = subparsers.add_parser("collect", help="只收集数据，不生成简报")
    collect_parser.set_defaults(func=cmd_collect)

    # briefing - 只生成简报
    briefing_parser = subparsers.add_parser("briefing", help="用已有数据生成简报")
    briefing_parser.add_argument("--date", help="Date (YYYY-MM-DD)")
    briefing_parser.set_defaults(func=cmd_briefing)

    # stats
    stats_parser = subparsers.add_parser("stats", help="查看统计信息")
    stats_parser.set_defaults(func=cmd_stats)

    # refetch - 重新抓取
    refetch_parser = subparsers.add_parser("refetch", help="重新抓取指定日期数据")
    refetch_parser.add_argument("date", help="Date (YYYY-MM-DD)")
    refetch_parser.set_defaults(func=cmd_refetch)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
