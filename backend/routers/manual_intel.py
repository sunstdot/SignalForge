"""手动情报录入 API"""
import asyncio
import re
from typing import Optional
from fastapi import APIRouter, HTTPException

from services.storage import (
    get_manual_intel_items,
    get_manual_intel_item_by_id,
    create_manual_intel_item,
    update_manual_intel_item,
    delete_manual_intel_item,
)
from services.llm_client import chat_async

router = APIRouter()


async def _fetch_url_content(url: str) -> tuple[str, str]:
    """Fetch a URL and return (title, content_snippet). Never raises — returns empty strings on failure."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 TokenBurner/1.0"}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return "", ""
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title else ""
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            snippet = soup.get_text(separator=" ", strip=True)[:6000]
            return title, snippet
    except Exception as e:
        print(f"[manual-intel] fetch failed for {url}: {e}")
        return "", ""


async def _run_ai_analysis(item_id: str):
    """Run quick_read, business_opps, rdev_opps in sequence and persist each result."""
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        return

    title = item.get("title", "")
    snippet = item.get("content_snippet", "")

    # -- Quick read --
    quick_read_prompt = f"""请对以下文章进行速读总结，帮助读者快速了解核心内容。

文章标题：{title}
原文内容（节选）：
{snippet}

请用中文输出，严格使用以下 Markdown 格式：
**核心内容**：用 2-3 句话说清楚文章讲了什么（面向技术/创业读者）

**关键信息**：
- 要点一
- 要点二
- 要点三（共 3-5 条，每条以 - 开头）

**值得关注**：这篇文章最有价值的一个洞察或信息（1 句话）

直接输出内容，不要重复标题。"""

    try:
        quick_read = (await chat_async([{"role": "user", "content": quick_read_prompt}])).strip()
        update_manual_intel_item(item_id, {"quick_read": quick_read})
    except Exception as e:
        print(f"[manual-intel] quick_read failed for {item_id}: {e}")

    # -- Business opportunities --
    biz_prompt = f"""你是一位经验丰富的 AI 产品经理和连续创业者，擅长从技术内容中发现真实可落地的商业机会。

# 开发者背景
- 独立开发者，无团队
- 技术栈：Python / Next.js
- 可接受面向全球或中文市场的产品

# 文章信息
标题：{title}
内容节选：{snippet[:3000]}

# 任务
基于以上文章，识别 1-3 个可落地的商业机会。如果文章内容无商业机会（纯商业新闻、人事变动等），返回空数组 []。

# 输出格式（严格 JSON，不要 markdown 代码块）
[
  {{
    "opportunity_title": "产品方向名称（30字以内）",
    "core_insight": "这个技术能力如何支撑此产品，之前为何不可行（60字以内）",
    "product_form": "帮助[目标用户]解决[具体问题]的[产品类型]",
    "target_users": "用户画像：职业/场景/痛点/付费意愿（40字以内）",
    "mvp_features": ["核心功能1", "核心功能2", "核心功能3"],
    "business_model": "盈利方式及定价（30字以内）",
    "risks": "最大风险（40字以内）",
    "scores": {{
      "pain_point": 4,
      "market_size": 3,
      "tech_timing": 5,
      "buildability": 4
    }},
    "total_score": 16
  }}
]"""

    try:
        import json as _json
        raw = (await chat_async([{"role": "user", "content": biz_prompt}], provider="deepseek")).strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        business_opps = _json.loads(match.group(0) if match else raw)
        if not isinstance(business_opps, list):
            business_opps = []
        update_manual_intel_item(item_id, {"business_opps": business_opps})
    except Exception as e:
        print(f"[manual-intel] business_opps failed for {item_id}: {e}")
        update_manual_intel_item(item_id, {"business_opps": []})

    # -- R&D opportunities --
    rdev_prompt = f"""你是一位深度嵌入顶级互联网大厂的 AI 架构师兼技术顾问，深知研发团队的真实痛点。

# 文章信息
标题：{title}
内容节选：{snippet[:3000]}

# 任务
基于以上文章，挖掘 1-3 个可落地的研发提效或业务赋能机会。如文章无技术内容，返回空数组 []。

# 输出格式（严格 JSON，不要 markdown 代码块）
[
  {{
    "type": "研发提效",
    "title": "一句话方案名称（20字以内）",
    "trigger": "哪个技术点触发了这个机会（30字以内）",
    "scenario": "在[具体场景]中，目前做法是[现有做法]，核心痛点在于[问题所在]（80字以内）",
    "ai_solution": "新技术如何重构这个场景（80字以内）",
    "implementation": "具体集成形态，如VS Code插件/GitLab Webhook等（60字以内）",
    "audience": ["大前端", "客户端"],
    "impact": "量化预期收益（50字以内）",
    "difficulty": "低",
    "scores": {{
      "efficiency": 8,
      "feasibility": 7,
      "business_impact": 6,
      "overall": 8
    }},
    "total_score": 8
  }}
]

type 只能是"研发提效"或"业务赋能"。difficulty 只能是"低"、"中"、"高"。"""

    try:
        import json as _json
        raw = (await chat_async([{"role": "user", "content": rdev_prompt}], provider="deepseek")).strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        rdev_opps = _json.loads(match.group(0) if match else raw)
        if not isinstance(rdev_opps, list):
            rdev_opps = []
        update_manual_intel_item(item_id, {"rdev_opps": rdev_opps})
    except Exception as e:
        print(f"[manual-intel] rdev_opps failed for {item_id}: {e}")
        update_manual_intel_item(item_id, {"rdev_opps": []})


@router.get("")
async def list_items(source_platform: Optional[str] = None):
    items = get_manual_intel_items(source_platform=source_platform)
    return {"items": items}


@router.get("/{item_id}")
async def get_item(item_id: str):
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("", status_code=201)
async def create_item(body: dict):
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url required")

    title, content_snippet = await _fetch_url_content(url)
    if not title:
        title = url  # fallback: use URL as title if fetch failed

    item = create_manual_intel_item({
        "url": url,
        "title": title,
        "source_platform": body.get("source_platform", "other"),
        "user_note": body.get("user_note", ""),
        "content_snippet": content_snippet,
    })

    asyncio.create_task(_run_ai_analysis(item["id"]))
    return item


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    ok = delete_manual_intel_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.post("/{item_id}/reanalyze")
async def reanalyze_item(item_id: str):
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    update_manual_intel_item(item_id, {"quick_read": "", "business_opps": [], "rdev_opps": []})
    asyncio.create_task(_run_ai_analysis(item_id))
    return {"ok": True, "message": "Re-analysis started"}
