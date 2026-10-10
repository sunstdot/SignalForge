"""内容相关 API"""
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from services.storage import get_content_items, get_content_item_by_id, get_content_stats, load_quick_reads, save_quick_read
from services.llm_client import chat_async

router = APIRouter()


@router.get("")
async def get_content(
    date: Optional[str] = None,
    source_type: Optional[str] = None,
    min_score: float = Query(0, ge=0, le=10),
    limit: int = Query(200, le=500),
):
    """获取内容列表"""
    items = get_content_items(date=date, source_type=source_type, min_score=min_score, limit=limit)
    return {"items": items}


@router.get("/stats")
async def get_content_stats_api():
    """获取内容统计"""
    return get_content_stats()


@router.get("/quick-reads/{date}")
async def get_quick_reads(date: str):
    """获取某日期所有已缓存的速读摘要"""
    return load_quick_reads(date)


@router.post("/quick-read")
async def quick_read(request: dict):
    """获取并 AI 总结原文内容（有缓存直接返回）"""
    item_id = request.get("item_id", "")
    url = request.get("url", "")
    title = request.get("title", "")
    date = request.get("date", datetime.now().strftime("%Y-%m-%d"))
    existing_summary = request.get("existing_summary", "")

    if not url:
        raise HTTPException(status_code=400, detail="url required")

    # 命中缓存直接返回
    cached = load_quick_reads(date)
    if item_id in cached:
        return {"summary": cached[item_id], "cached": True}

    # 抓取原文
    raw_text = ""
    try:
        import httpx
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 TokenBurner/1.0"}) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # 移除导航、脚注等噪音
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                raw_text = soup.get_text(separator=" ", strip=True)[:6000]
    except Exception as e:
        print(f"[quick-read] fetch failed: {e}")

    # 构建 AI 摘要 prompt
    content_section = f"原文内容（节选）：\n{raw_text}" if raw_text else \
                      f"原文无法获取，基于已有摘要：\n{existing_summary}"

    prompt = f"""请对以下文章进行速读总结，帮助读者快速了解核心内容。

文章标题：{title}
{content_section}

请用中文输出，严格使用以下 Markdown 格式：
**核心内容**：用 2-3 句话说清楚文章讲了什么（面向技术/创业读者）

**关键信息**：
- 要点一
- 要点二
- 要点三（共 3-5 条，每条以 - 开头）

**值得关注**：这篇文章最有价值的一个洞察或信息（1 句话）

直接输出内容，不要重复标题。"""

    try:
        summary = (await chat_async([{"role": "user", "content": prompt}])).strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)[:200]}")

    # 缓存
    if item_id:
        save_quick_read(date, item_id, summary)

    return {"summary": summary, "cached": False}


class PaperQuickReadRequest(BaseModel):
    item_id: str = Field(min_length=1)


@router.post("/paper-quick-read")
async def paper_quick_read(request: PaperQuickReadRequest):
    from services.paper_quick_read import read_paper

    item = get_content_item_by_id(request.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到这篇论文，请刷新页面后重试。")
    if item.get("source_type") not in {"paper", "arxiv"}:
        raise HTTPException(status_code=400, detail="论文速读仅支持论文条目。")
    url = urlparse(item.get("url") or "")
    if url.scheme not in {"http", "https"} or not url.hostname:
        raise HTTPException(status_code=400, detail="论文缺少有效的原文链接。")
    try:
        return await read_paper(item)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="论文速读超时，请稍后重试。")
    except Exception:
        raise HTTPException(status_code=502, detail="论文速读生成失败，请重试；若持续失败，请检查 Wingsbot 服务与模型配置。")


@router.get("/{id}")
async def get_content_item(id: str):
    """获取单个内容详情"""
    item = get_content_item_by_id(id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item
