"""简报相关 API"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.briefing_generator import get_briefing_by_date, get_latest_briefing, get_briefing_markdown

router = APIRouter()


class BriefingResponse(BaseModel):
    id: str
    date: str
    items: list
    summary: Optional[str]
    generated_at: str


@router.get("/latest")
async def get_latest():
    """获取最新简报"""
    briefing = get_latest_briefing()
    if not briefing:
        raise HTTPException(status_code=404, detail="No briefing found")
    return briefing


@router.get("/{date}")
async def get_briefing(date: str):
    """获取指定日期的简报"""
    import re
    
    # 验证日期格式
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    briefing = get_briefing_by_date(date)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return briefing


@router.get("/{date}/markdown")
async def get_briefing_md(date: str):
    """获取简报的 Markdown 格式"""
    import re
    
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    markdown = get_briefing_markdown(date)
    return {"markdown": markdown}
