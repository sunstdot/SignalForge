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
from services.collector import run_collection, run_daily, load_config, _run_batch_quick_reads
from services.llm_client import chat


def cmd_daily(args):
    """一键运行：收集 → 生成简报"""
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    asyncio.run(run_daily(date))


def cmd_collect(args):
    """运行数据收集"""
    print("🚀 Starting data collection...")
    target_date = getattr(args, 'date', None)
    asyncio.run(run_collection(target_date=target_date))


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


def cmd_summarize(args):
    """只执行速读摘要生成（数据已收集，跳过 run_collection）"""
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    print(f"📝 Generating quick-read summaries for {date}...")
    _run_batch_quick_reads(date)


def cmd_quick_reads(args):
    """批量预生成速读摘要"""
    import asyncio as _asyncio
    import httpx

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    print(f"⚡ Batch generating quick-reads for {date}...")

    # 直接调用内部逻辑，无需 HTTP（复用 briefing router 的逻辑）
    from services.briefing_generator import get_briefing_by_date
    from services.storage import load_quick_reads, save_quick_read
    import re as _re, json as _json

    briefing = get_briefing_by_date(date)
    if not briefing:
        print(f"❌ No briefing found for {date}")
        return

    cached = load_quick_reads(date)
    to_process = [i for i in briefing["items"] if i.get("summary") and i["id"] not in cached]

    if not to_process:
        print(f"✅ All {len(cached)} items already cached, nothing to do")
        return

    print(f"  Processing {len(to_process)} items ({len(cached)} already cached)...")


    BATCH_SIZE = 15
    generated = 0

    for batch_start in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[batch_start:batch_start + BATCH_SIZE]
        print(f"  Batch {batch_start // BATCH_SIZE + 1}: {len(batch)} items...", end=" ", flush=True)

        items_text = "\n".join(
            f"[{idx}] 标题：{item['title']}\n    摘要：{(item.get('summary') or '')[:500]}"
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

        def _sanitize_json(text: str) -> str:
            """修复 LLM 输出的 JSON 中字符串值里的裸换行符"""
            # 将 JSON 字符串值内的裸换行/回车/制表替换为转义序列
            result = []
            in_string = False
            escape_next = False
            for ch in text:
                if escape_next:
                    result.append(ch)
                    escape_next = False
                elif ch == '\\' and in_string:
                    result.append(ch)
                    escape_next = True
                elif ch == '"':
                    in_string = not in_string
                    result.append(ch)
                elif in_string and ch == '\n':
                    result.append('\\n')
                elif in_string and ch == '\r':
                    result.append('\\r')
                elif in_string and ch == '\t':
                    result.append('\\t')
                else:
                    result.append(ch)
            return ''.join(result)

        def _parse_llm_json(raw: str):
            raw = _re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
            match = _re.search(r'\[.*\]', raw, _re.DOTALL)
            json_str = match.group(0) if match else raw
            try:
                return _json.loads(json_str)
            except _json.JSONDecodeError:
                return _json.loads(_sanitize_json(json_str))

        def _save_result(r, real_idx):
            if real_idx < len(to_process):
                item = to_process[real_idx]
                points_md = "\n".join(f"- {p}" for p in (r.get("points") or []))
                summary = f"**核心内容**：{r.get('core', '')}\n\n**关键信息**：\n{points_md}\n\n**值得关注**：{r.get('insight', '')}"
                save_quick_read(date, item["id"], summary)
                return True
            return False

        try:
            raw = chat([{"role": "user", "content": prompt}]).strip()
            results = _parse_llm_json(raw)

            count = 0
            for r in results:
                real_idx = batch_start + r["idx"] - 1
                if _save_result(r, real_idx):
                    generated += 1
                    count += 1
            print(f"✓ {count} generated")
        except Exception as e:
            print(f"✗ batch failed ({e}), falling back to item-by-item...")
            # 逐条重试，避免整批丢失
            for i, item in enumerate(batch):
                single_prompt = f"""对以下文章生成速读总结，输出单个 JSON 对象（只输出 JSON，不要 markdown 代码块）。

标题：{item['title']}
摘要：{(item.get('summary') or '')[:500]}

输出格式（每个字段都是单行字符串，不含换行符）：
{{
  "idx": 1,
  "core": "核心内容：2-3句话概括文章",
  "points": ["要点一", "要点二", "要点三"],
  "insight": "最有价值的一个洞察（1句话）"
}}"""
                try:
                    raw_s = chat([{"role": "user", "content": single_prompt}]).strip()
                    raw_s = _re.sub(r'^```[a-z]*\n?', '', raw_s).rstrip('`').strip()
                    match_s = _re.search(r'\{.*\}', raw_s, _re.DOTALL)
                    r = _json.loads(_sanitize_json(match_s.group(0) if match_s else raw_s))
                    r["idx"] = i + 1
                    if _save_result(r, batch_start + i):
                        generated += 1
                        print(f"    ✓ [{batch_start + i + 1}] {item['title'][:40]}")
                except Exception as e2:
                    print(f"    ✗ [{batch_start + i + 1}] {item['title'][:40]}: {e2}")

    print(f"\n✅ Done: {generated} quick-reads generated for {date}")


def cmd_chinese(args):
    """生成中文简报"""
    from services.chinese_briefer import generate_daily_chinese_briefing
    
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    limit = args.limit
    
    print(f"🇨🇳 Generating Chinese briefing for {date}...")
    if limit:
        print(f"   限制处理前 {limit} 条资讯")
    
    try:
        markdown = generate_daily_chinese_briefing(date, limit)
        
        # 保存到文件
        output_dir = os.path.join(os.path.dirname(__file__), "docs", "daily-briefings")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{date}-chinese.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        print(f"\n✅ 中文简报已保存到: {output_path}")
        
        # 显示预览
        if args.preview:
            print("\n" + "="*60)
            print("预览 (前 500 字符):")
            print("="*60)
            print(markdown[:500])
            print("...\n")
        
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()


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
    collect_parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)，默认今日")
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

    # summarize - 只跑速读摘要生成（数据已收集）
    summarize_parser = subparsers.add_parser("summarize", help="只生成速读摘要，跳过数据收集")
    summarize_parser.add_argument("--date", help="Date (YYYY-MM-DD), default today")
    summarize_parser.set_defaults(func=cmd_summarize)

    # quick-reads - 批量预生成速读
    qr_parser = subparsers.add_parser("quick-reads", help="批量预生成速读摘要（用已有 summary）")
    qr_parser.add_argument("--date", help="Date (YYYY-MM-DD), default today")
    qr_parser.set_defaults(func=cmd_quick_reads)

    # chinese - 生成中文简报
    chinese_parser = subparsers.add_parser("chinese", help="生成中文简报")
    chinese_parser.add_argument("--date", help="Date (YYYY-MM-DD), default today")
    chinese_parser.add_argument("--limit", type=int, help="最多处理几条资讯 (默认全部)")
    chinese_parser.add_argument("--preview", action="store_true", help="显示预览")
    chinese_parser.set_defaults(func=cmd_chinese)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
