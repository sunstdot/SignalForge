"""简报生成服务 - 基于文件存储"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .storage import _load_content_file, get_all_dates, save_briefing_file
import json
import uuid


def get_briefing_by_date(date: str) -> Optional[Dict]:
    """获取指定日期的简报（始终从内容文件动态生成）"""
    return generate_briefing_for_date(date)


def get_latest_briefing() -> Optional[Dict]:
    """获取最新简报"""
    dates = get_all_dates()
    if not dates:
        return None
    return generate_briefing_for_date(dates[0])


def generate_briefing_for_date(date: str) -> Optional[Dict]:
    """为指定日期生成简报：聚合最近 3 天的内容"""
    # 收集最近 3 天的内容
    since_dt = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=3)
    all_items = []

    dates = get_all_dates()
    for d in dates:
        if d < since_dt.strftime("%Y-%m-%d"):
            break
        if d > date:
            continue
        all_items.extend(_load_content_file(d))

    if not all_items:
        return None

    # 去重
    seen_ids = set()
    unique_items = []
    for item in all_items:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            unique_items.append(item)

    # 按来源类型分组，每类取 top N，保证各类都有内容
    type_limits = {
        "arxiv": 15,
        "paper": 15,
        "github": 20,
        "repo": 20,
        "model": 20,
        "rss": 50,
        "smolai": 10,
        "newsletter": 10,
        "news": 20,
    }

    by_type: Dict[str, List] = {}
    for item in unique_items:
        t = item.get("source_type", "other")
        by_type.setdefault(t, []).append(item)

    items = []
    for t, type_items in by_type.items():
        limit = type_limits.get(t, 10)
        type_items.sort(key=lambda x: -x.get("relevance_score", 0))
        items.extend(type_items[:limit])

    # 最终排序：按 relevance_score 降序
    items.sort(key=lambda x: -x.get("relevance_score", 0))

    result_items = []
    for item in items:
        result_items.append({
            "id": item["id"],
            "title": item["title"],
            "source": item["source"],
            "source_type": item["source_type"],
            "url": item["url"],
            "summary": item.get("summary") or (item.get("original_content") or "")[:200],
            "category": item.get("category", []),
            "relevance_score": item.get("relevance_score", 0),
            "created_at": item.get("created_at", ""),
        })

    briefing = {
        "id": str(uuid.uuid4()),
        "date": date,
        "items": result_items,
        "summary": None,
        "generated_at": datetime.now().isoformat(),
    }

    # 同时保存简报文件供参考
    save_briefing_file(briefing)

    return briefing


def get_briefing_markdown(date: str) -> str:
    """生成简报的 Markdown 格式"""
    briefing = get_briefing_by_date(date)

    if not briefing:
        return f"# {date} 简报\n\n暂无数据"

    lines = [
        f"# {date} AI 技术日报",
        "",
        f"> 生成时间: {briefing['generated_at'][:19]}  ",
        f"> 共 {len(briefing['items'])} 条内容",
        "",
    ]

    # 按 source_type 分组
    groups: Dict[str, List] = {}
    for item in briefing["items"]:
        st = item["source_type"]
        groups.setdefault(st, []).append(item)

    type_labels = {
        "paper": "📄 学术论文",
        "arxiv": "📄 arXiv 论文",
        "repo": "⭐ GitHub Trending",
        "github": "⭐ GitHub Trending",
        "model": "🤖 模型动态",
        "rss": "📰 博客与资讯",
        "news": "📰 新闻",
        "newsletter": "📬 Newsletter",
        "smolai": "🤖 SmolAI 资讯",
    }

    for source_type, group_items in groups.items():
        label = type_labels.get(source_type, f"📌 {source_type}")
        lines.append(f"## {label}")
        lines.append("")
        for item in group_items:
            lines.append(f"### [{item['title']}]({item['url']})")
            lines.append(f"*{item['source']}*")
            if item.get("summary"):
                lines.append(f"\n{item['summary'][:300]}")
            lines.append("")

    return "\n".join(lines)
