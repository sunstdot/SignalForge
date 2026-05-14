"""AI 客户端服务"""
import json

from .llm_client import chat


def filter_content(item: dict) -> dict:
    """AI 内容过滤"""
    prompt = f"""分析以下内容的相关性和分类:

标题: {item['title']}
内容: {item['original_content'][:1000]}

请输出 JSON 格式:
{{
    "score": 1-10 的相关性评分,
    "categories": ["分类1", "分类2"],
    "reason": "评分理由"
}}"""

    try:
        result = json.loads(chat([{"role": "user", "content": prompt}]))
        return {
            "score": result.get("score", 5),
            "categories": result.get("categories", ["未分类"]),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        print(f"Filter error: {e}")
        return {"score": 5, "categories": ["未分类"], "reason": "AI 处理失败"}


def summarize_content(item: dict) -> dict:
    """AI 内容摘要"""
    prompt = f"""对以下内容生成摘要和洞察:

标题: {item['title']}
内容: {item['original_content'][:2000]}

请输出 JSON 格式:
{{
    "summary": "100字以内的摘要",
    "insights": ["洞察1", "洞察2"]
}}"""

    try:
        result = json.loads(chat([{"role": "user", "content": prompt}]))
        return {
            "summary": result.get("summary", ""),
            "insights": result.get("insights", []),
        }
    except Exception as e:
        print(f"Summarize error: {e}")
        return {"summary": "", "insights": []}
