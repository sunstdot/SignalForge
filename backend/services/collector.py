"""内容收集服务 - 主控逻辑"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict
import yaml

from .storage import store_content_items, get_all_dates, _load_content_file
from .rss_fetcher import fetch_rss_feeds
from .arxiv_fetcher import fetch_arxiv_papers
from .github_fetcher import fetch_github_trending
from .models_fetcher import fetch_model_platforms


async def run_collection():
    """运行数据收集"""
    print("🚀 TokenBurner Collector starting...\n")

    config = load_config()
    print("✓ Configuration loaded")

    # 并发抓取所有数据源
    print("\n📥 Fetching data from all sources...")
    all_items = await fetch_all_sources(config)
    print(f"\n✓ Total fetched: {len(all_items)} items")

    # 存储到文件
    stored = store_content_items(all_items)
    print(f"✓ Stored {stored} new items")

    print("\n🎉 Collection completed!")
    return stored


async def run_daily(date: str):
    """一键运行：收集 → 生成简报"""
    print(f"📅 Running daily pipeline for {date}\n")

    print("=" * 50)
    print("Step 1/2: 数据收集")
    print("=" * 50)
    stored = await run_collection()

    print("\n" + "=" * 50)
    print("Step 2/2: 生成简报")
    print("=" * 50)
    from .briefing_generator import generate_briefing_for_date, get_briefing_markdown
    briefing = generate_briefing_for_date(date)

    if briefing:
        items_count = len(briefing.get("items", []))
        print(f"✓ Briefing generated with {items_count} items")

        # 保存 Markdown
        markdown = get_briefing_markdown(date)
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "daily-briefings")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{date}.md")
        with open(output_path, "w") as f:
            f.write(markdown)
        print(f"✓ Saved to {output_path}")
    else:
        print("⚠️  No items found for briefing")

    # 统计
    print("\n" + "=" * 50)
    print("📊 Summary")
    print("=" * 50)
    today_items = _load_content_file(date)
    by_type: Dict[str, int] = {}
    for item in today_items:
        t = item.get("source_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    print(f"  Today's items: {len(today_items)}")
    for t, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {t:15} {cnt:>4}")
    print(f"\n✅ Daily pipeline completed for {date}!")


async def fetch_all_sources(config: Dict) -> List[Dict]:
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
        tasks.append(("RSS", fetch_rss_feeds(sources_config["rss"])))

    if sources_config.get("smolai", {}).get("enabled"):
        from .smolai_fetcher import fetch_smolai_news
        tasks.append(("SmolAI", fetch_smolai_news(sources_config["smolai"])))

    all_items = []
    results = await asyncio.gather(
        *[coro for _, coro in tasks],
        return_exceptions=True
    )

    for (name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            print(f"  ✗ {name} failed: {result}")
        elif isinstance(result, list):
            # 策展内容统一设置高相关度分数
            for item in result:
                if item.get("relevance_score", 0) == 0:
                    item["relevance_score"] = 8
            all_items.extend(result)
            print(f"  ✓ {name}: {len(result)} items")
        else:
            print(f"  ✗ {name}: unexpected result")

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
