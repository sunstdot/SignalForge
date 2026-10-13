"""简报生成服务 - 基于文件存储"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .storage import _load_content_file, get_all_dates, load_quick_reads, save_briefing_file
from .signal_feed import build_signal_feed
from .source_run_store import load_source_run
from .event_radar import load_event_radar
from .x_account_daily import load_x_account_day
import json
import uuid


FEED_SOURCE_TYPES = {"rss", "blog", "news", "newsletter", "smolai", "hackernews", "investor", "wechat"}


def _parse_item_datetime(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        raw = value.strip()
        try:
            if len(raw) == 10:
                dt = datetime.strptime(raw, "%Y-%m-%d")
            else:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def _is_recent_feed_item(item: Dict, fetched_at: datetime) -> bool:
    """Feed 条目发布时间超过 7 天则不进入简报候选。"""
    if item.get("source_type") not in FEED_SOURCE_TYPES:
        return True

    published_at = _parse_item_datetime(
        item.get("published_at") or item.get("published_date") or item.get("created_at")
    )
    if published_at is None:
        return True

    return fetched_at - published_at <= timedelta(days=7)


def get_briefing_by_date(date: str) -> Optional[Dict]:
    """获取指定日期的简报（始终从内容文件动态生成）"""
    return generate_briefing_for_date(date)


def get_latest_briefing() -> Optional[Dict]:
    """获取最新简报"""
    dates = get_all_dates()
    if not dates:
        return None
    return generate_briefing_for_date(dates[0])


def make_account_card(post: dict, quick_reads: dict[str, str]) -> dict:
    """A saved quick read is optional; a raw excerpt is not a model opinion."""
    metadata = post.get('metadata') or {}
    quick_read = quick_reads.get(post['id'])
    card = {
        'id': post['id'], 'handle': metadata.get('account', ''),
        'kind': metadata.get('post_type', ''), 'title': post.get('title', ''),
        'url': post['url'], 'published_at': post.get('published_at', ''),
        'takeaway': quick_read or (post.get('original_content') or post.get('summary') or '')[:600],
        'text_type': 'quick_read' if quick_read else 'original_excerpt',
    }
    if metadata.get('quoted_url'):
        card['quoted_url'] = metadata['quoted_url']
    return card


def generate_briefing_for_date(date: str) -> Optional[Dict]:
    """为指定日期生成简报：优先当天内容，不足时向前补充最多 2 天"""
    fetched_at = datetime.now()
    signal_date = datetime.strptime(date, "%Y-%m-%d")
    dates = get_all_dates()
    all_dates_in_range = [d for d in dates if d <= date]

    # 仅读取已落盘的研究结果；GET 不进行搜索或调用模型。
    source_status = load_source_run(date)
    radar = load_event_radar(date)
    account_state = load_x_account_day(date)
    has_radar_state = bool(source_status) or bool(radar)
    has_daily_state = has_radar_state or bool(account_state)
    today_items = _load_content_file(date)
    today_types = {i.get("source_type") for i in today_items}

    # 对当天缺失的 source_type，用前一天的补充（最多回溯 2 天）
    # 注意：只补充当天完全没有的类型，已有的类型不用前日内容，避免重复
    fallback_items = []
    IMPORTANT_TYPES = {"repo", "github", "arxiv", "paper", "rss", "hackernews"}
    missing_types = IMPORTANT_TYPES - today_types

    for extra_day in range(1, 3):
        # 当天所有信源失败时展示故障，而非将昨日信息冒充今日发现。
        if not missing_types or (not today_items and has_daily_state):
            break
        prev = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=extra_day)).strftime("%Y-%m-%d")
        if prev not in all_dates_in_range:
            continue
        prev_items = _load_content_file(prev)
        for item in prev_items:
            t = item.get("source_type")
            if t in missing_types:
                fallback_items.append(item)
        # 记录哪些类型已从 prev 补充到了
        filled = {i.get("source_type") for i in fallback_items}
        missing_types -= filled

    all_items = [
        item for item in today_items + fallback_items
        if _is_recent_feed_item(item, fetched_at)
    ]

    if not all_items and not has_daily_state:
        return None

    # 去重（优先保留当天的，created_at 较大的优先）
    seen_ids: set = set()
    unique_items = []
    for item in sorted(all_items, key=lambda x: x.get("created_at", ""), reverse=True):
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
        "blog": 20,
        "rss": 50,
        "smolai": 15,
        "hackernews": 20,
        "newsletter": 10,
        "news": 20,
        "anthropic_blog": 5,
    }
    PER_SOURCE_LIMIT = 3  # 每个具体 source 最多 3 条，避免单源垄断
    # 聚合源（每条来自不同项目/论文），不受 per-source 限制
    NO_PER_SOURCE_LIMIT_TYPES = {"arxiv", "paper", "github", "repo", "model", "smolai", "hackernews", "anthropic_blog"}

    by_type: Dict[str, List] = {}
    for item in unique_items:
        t = item.get("source_type", "other")
        by_type.setdefault(t, []).append(item)

    items = []
    for t, type_items in by_type.items():
        limit = type_limits.get(t, 10)
        if t == "anthropic_blog":
            type_items.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        else:
            type_items.sort(key=lambda x: -x.get("relevance_score", 0))
        # 先做每类 top N，再做每 source 限流（聚合源跳过限流）
        source_counts: Dict[str, int] = {}
        skip_per_source = t in NO_PER_SOURCE_LIMIT_TYPES
        for item in type_items:
            if len([i for i in items if i.get("source_type") == t]) >= limit:
                break
            src = item.get("source", "")
            if not skip_per_source and source_counts.get(src, 0) >= PER_SOURCE_LIMIT:
                continue
            source_counts[src] = source_counts.get(src, 0) + 1
            items.append(item)

    # 最终排序：普通条目按相关度，Agent 获取的 Anthropic 文章固定追加到末尾。
    regular_items = [item for item in items if item.get("source_type") != "anthropic_blog"]
    anthropic_items = [item for item in items if item.get("source_type") == "anthropic_blog"]
    regular_items.sort(key=lambda x: -x.get("relevance_score", 0))
    anthropic_items.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    items = regular_items + anthropic_items

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

    quick_reads = load_quick_reads(date)
    signals = build_signal_feed(
        [item for item in today_items if _is_recent_feed_item(item, signal_date)],
        quick_reads,
    )
    if has_radar_state:
        signals['events'] = radar.get('events', [])
        signals['source_status'] = source_status
        signals['selection_status'] = radar.get('selection_status', 'unavailable' if radar else 'not_run')
    if account_state:
        signals['accounts'] = [
            {
                'handle': handle, 'status': entry.get('status', 'unavailable'),
                'checked_at': entry.get('checked_at', ''), 'reason': entry.get('reason', ''),
                'posts': [make_account_card(post, quick_reads)
                          for post in entry.get('posts', [])],
            }
            for handle, entry in account_state.get('accounts', {}).items()
        ]
    briefing = {
        "id": str(uuid.uuid4()),
        "date": date,
        "items": result_items,
        "signals": signals,
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
