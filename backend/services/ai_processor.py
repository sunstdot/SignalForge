"""AI 处理服务 - 内容过滤和摘要"""
import json
import os
from typing import Dict, List
from openai import OpenAI

_client = None


def get_ai_client():
    """获取 AI 客户端"""
    global _client
    if _client is None:
        api_key = os.getenv("WANQING_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("WANQING_BASE_URL") or os.getenv("OPENROUTER_BASE_URL")
        
        if base_url:
            _client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            _client = OpenAI(api_key=api_key)
    return _client


def filter_content(item: Dict) -> Dict:
    """AI 内容过滤 - 评估相关性"""
    client = get_ai_client()
    
    # RSS 源和模型平台自动通过（手动策展的源默认信任）
    if item.get("source_type") in ("rss", "model"):
        return {
            "score": 8,
            "categories": item.get("category", ["技术资讯"]),
            "reason": "Curated source - auto pass"
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
        response = client.chat.completions.create(
            model=os.getenv("AI_MODEL", "gpt-4"),
            messages=[
                {"role": "system", "content": "你是一个专业的技术内容筛选助手，只输出 JSON 格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        
        # 尝试解析 JSON
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON
            json_match = json.loads(_extract_json(content))
            result = json_match if json_match else {
                "score": 5,
                "categories": ["未分类"],
                "reason": "Parse error"
            }
        
        return {
            "score": max(1, min(10, int(result.get("score", 5)))),
            "categories": result.get("categories", ["未分类"])[:3],
            "reason": result.get("reason", "")
        }
        
    except Exception as e:
        print(f"Filter error: {e}")
        return {
            "score": 5,
            "categories": ["未分类"],
            "reason": f"AI error: {str(e)[:50]}"
        }


def summarize_content(item: Dict) -> Dict:
    """AI 内容摘要"""
    client = get_ai_client()
    
    content_text = item.get('raw_text', item.get('original_content', ''))[:3000]
    
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
        response = client.chat.completions.create(
            model=os.getenv("AI_MODEL", "gpt-4"),
            messages=[
                {"role": "system", "content": "你是一个专业的技术内容分析助手，只输出 JSON 格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        
        content = response.choices[0].message.content
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            json_match = json.loads(_extract_json(content))
            result = json_match if json_match else {
                "summary": content[:200],
                "insights": []
            }
        
        return {
            "summary": result.get("summary", "")[:300],
            "insights": result.get("insights", [])[:5]
        }
        
    except Exception as e:
        print(f"Summarize error: {e}")
        return {
            "summary": "",
            "insights": []
        }


def generate_daily_briefing(items: List[Dict]) -> str:
    """生成每日简报 Markdown"""
    client = get_ai_client()
    
    # 构建内容
    content_parts = []
    for item in items[:15]:  # 最多 15 条
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
        response = client.chat.completions.create(
            model=os.getenv("AI_MODEL", "gpt-4"),
            messages=[
                {"role": "system", "content": "你是一位技术新闻编辑，擅长撰写简洁有力的每日简报。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Briefing generation error: {e}")
        # 返回简单的默认简报
        lines = ["# 每日简报\n"]
        for item in items[:10]:
            lines.append(f"## {item['title']}")
            lines.append(f"*{item['source']}*\n")
            lines.append(f"{item.get('summary', 'No summary')}\n")
        return "\n".join(lines)


def _extract_json(text: str) -> str:
    """从文本中提取 JSON"""
    # 寻找 JSON 代码块
    import re
    
    # 尝试匹配 ```json ... ```
    match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    
    # 尝试匹配直接的 JSON 对象
    match = re.search(r'({.*?})', text, re.DOTALL)
    if match:
        return match.group(1)
    
    return text
