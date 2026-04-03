"""内容相关 API"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from services.storage import get_content_items, get_content_item_by_id, get_content_stats

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


@router.get("/{id}")
async def get_content_item(id: str):
    """获取单个内容详情"""
    item = get_content_item_by_id(id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item
