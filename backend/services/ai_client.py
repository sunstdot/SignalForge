"""AI 客户端服务"""
import os
from openai import OpenAI

_client = None


def get_ai_client():
    """获取 AI 客户端（单例模式）"""
    global _client
    if _client is None:
        # 优先使用晚晴 API，其次 OpenRouter
        api_key = os.getenv("WANQING_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("WANQING_BASE_URL") or os.getenv("OPENROUTER_BASE_URL")
        
        if base_url:
            _client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            _client = OpenAI(api_key=api_key)
    return _client


def filter_content(item: dict) -> dict:
    """AI 内容过滤"""
    client = get_ai_client()
    
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
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        import json
        result = json.loads(response.choices[0].message.content)
        return {
            "score": result.get("score", 5),
            "categories": result.get("categories", ["未分类"]),
            "reason": result.get("reason", "")
        }
    except Exception as e:
        print(f"Filter error: {e}")
        return {"score": 5, "categories": ["未分类"], "reason": "AI 处理失败"}


def summarize_content(item: dict) -> dict:
    """AI 内容摘要"""
    client = get_ai_client()
    
    prompt = f"""对以下内容生成摘要和洞察:

标题: {item['title']}
内容: {item['original_content'][:2000]}

请输出 JSON 格式:
{{
    "summary": "100字以内的摘要",
    "insights": ["洞察1", "洞察2"]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        import json
        result = json.loads(response.choices[0].message.content)
        return {
            "summary": result.get("summary", ""),
            "insights": result.get("insights", [])
        }
    except Exception as e:
        print(f"Summarize error: {e}")
        return {"summary": "", "insights": []}
