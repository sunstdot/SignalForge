"""AI 处理服务 - 内容过滤和摘要"""
import json
import re
from typing import Dict, List

from .llm_client import chat


def filter_content(item: Dict) -> Dict:
    """AI 内容过滤 - 评估相关性"""
    if item.get("source_type") in ("rss", "model"):
        return {
            "score": 8,
            "categories": item.get("category", ["技术资讯"]),
            "reason": "Curated source - auto pass",
        }

    prompt = f"""你是一位技术内容筛选专家。请分析以下内容的相关性和分类:

标题: {item['title']}
来源: {item['source']}
内容: {item.get('original_content', '')[:1500]}

请评估:
1. 相关性评分 (1-10): 对 AI/技术从业者有多大价值？
2. 分类: 适合哪些分类标签？
3. 理由: 简要说明评分原因

请以 JSON 格式输出:
{{
    "score": 数字1-10,
    "categories": ["分类1", "分类2"],
    "reason": "评分理由"
}}"""

    try:
        content = chat(
            [{"role": "user", "content": prompt}],
            system_prompt="你是一个专业的技术内容筛选助手，只输出 JSON 格式。",
        )
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = json.loads(_extract_json(content)) or {
                "score": 5, "categories": ["未分类"], "reason": "Parse error"
            }
        return {
            "score": max(1, min(10, int(result.get("score", 5)))),
            "categories": result.get("categories", ["未分类"])[:3],
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        print(f"Filter error: {e}")
        return {"score": 5, "categories": ["未分类"], "reason": f"AI error: {str(e)[:50]}"}


def summarize_content(item: Dict) -> Dict:
    """AI 内容摘要"""
    content_text = item.get("raw_text", item.get("original_content", ""))[:3000]

    prompt = f"""请为以下内容生成简洁的摘要和关键洞察:

标题: {item['title']}
来源: {item['source']}
内容: {content_text}

要求:
1. 摘要: 100字以内，概括核心内容
2. 洞察: 2-3 个关键要点或价值点

请以 JSON 格式输出:
{{
    "summary": "摘要内容",
    "insights": ["洞察1", "洞察2", "洞察3"]
}}"""

    try:
        content = chat(
            [{"role": "user", "content": prompt}],
            system_prompt="你是一个专业的技术内容分析助手，只输出 JSON 格式。",
        )
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = json.loads(_extract_json(content)) or {"summary": content[:200], "insights": []}
        return {
            "summary": result.get("summary", "")[:300],
            "insights": result.get("insights", [])[:5],
        }
    except Exception as e:
        print(f"Summarize error: {e}")
        return {"summary": "", "insights": []}


def generate_daily_briefing(items: List[Dict]) -> str:
    """生成每日简报 Markdown"""
    content_parts = []
    for item in items[:15]:
        content_parts.append(f"""
标题: {item['title']}
来源: {item['source']}
摘要: {item.get('summary', 'N/A')}
分类: {', '.join(item.get('category', []))}
---
""")

    prompt = f"""基于以下内容，生成一份每日技术简报:

{''.join(content_parts)}

要求:
1. 写一个简短的概述段落（100字以内）
2. 按主题组织内容
3. 突出重要新闻
4. 使用 Markdown 格式

直接输出 Markdown 内容。"""

    try:
        return chat(
            [{"role": "user", "content": prompt}],
            system_prompt="你是一位技术新闻编辑，擅长撰写简洁有力的每日简报。",
        )
    except Exception as e:
        print(f"Briefing generation error: {e}")
        lines = ["# 每日简报\n"]
        for item in items[:10]:
            lines.append(f"## {item['title']}")
            lines.append(f"*{item['source']}*\n")
            lines.append(f"{item.get('summary', 'No summary')}\n")
        return "\n".join(lines)


def _extract_json(text: str) -> str:
    match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'({.*?})', text, re.DOTALL)
    if match:
        return match.group(1)
    return text
