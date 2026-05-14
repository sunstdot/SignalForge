"""中文简报生成服务"""
import json
import os
import re
from typing import Dict

from .llm_client import chat


def generate_chinese_brief(item: Dict) -> Dict:
    """为单个资讯生成中文简报"""
    title = item.get("title", "")
    content = item.get("raw_text") or item.get("original_content", "")
    source = item.get("source", "")
    url = item.get("url", "")
    content_preview = content[:3000] if content else ""

    prompt = f"""请对以下英文技术资讯生成中文简报:

标题: {title}
来源: {source}
链接: {url}

内容:
{content_preview}

请用中文输出 JSON 格式:
{{
    "chinese_title": "中文标题翻译",
    "chinese_summary": "200字以内的中文摘要,概括核心内容和要点",
    "chinese_insights": ["洞察要点1", "洞察要点2", "洞察要点3"],
    "key_topics": ["关键主题1", "关键主题2"]
}}

要求:
1. 标题翻译要准确且易读,保留专业术语
2. 摘要要抓住核心信息,突出技术价值和创新点
3. 洞察要点提炼2-3个关键发现或启示
4. 关键主题标签提取2-3个核心概念
"""
    try:
        content_text = chat([{"role": "user", "content": prompt}])

        try:
            result = json.loads(content_text)
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content_text, re.DOTALL)
            if match:
                result = json.loads(match.group(1))
            else:
                match = re.search(r'(\{.*\})', content_text, re.DOTALL)
                if match:
                    result = json.loads(match.group(1))
                else:
                    raise ValueError("Cannot parse JSON from response")

        return {
            "chinese_title": result.get("chinese_title", title),
            "chinese_summary": result.get("chinese_summary", ""),
            "chinese_insights": result.get("chinese_insights", [])[:5],
            "key_topics": result.get("key_topics", [])[:5],
        }

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error generating Chinese brief: {error_msg[:200]}")
        if os.getenv("DEBUG", "").lower() == "true":
            import traceback
            traceback.print_exc()
        return {
            "chinese_title": title,
            "chinese_summary": f"生成摘要时出错: {error_msg[:100]}",
            "chinese_insights": [],
            "key_topics": [],
        }


def generate_daily_chinese_briefing(date: str, limit: int = None) -> str:
    """为指定日期生成完整的中文日报 Markdown"""
    from .storage import _load_content_file
    from datetime import datetime

    items = _load_content_file(date)
    if not items:
        return f"# {date} AI 技术日报 (中文版)\n\n暂无数据\n"

    if limit:
        items = items[:limit]

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

    groups: dict = {}
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
                lines.append(chinese_summary)
                lines.append("")
            if chinese_insights:
                lines.append("**关键洞察:**")
                for insight in chinese_insights:
                    lines.append(f"- {insight}")
                lines.append("")
            if key_topics:
                lines.append(f"**主题标签:** {' '.join(f'`{t}`' for t in key_topics)}")
                lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)
