"""日期相关 API"""
from fastapi import APIRouter
from services.storage import get_all_dates

router = APIRouter()


@router.get("")
async def get_dates():
    """获取所有有数据的日期列表"""
    dates = get_all_dates()
    return {"dates": dates}


@router.get("/adjacent/{date}")
async def get_adjacent_dates(date: str):
    """获取指定日期的前后日期"""
    import re

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return {"error": "Invalid date format"}

    dates = get_all_dates()  # sorted descending
    try:
        idx = dates.index(date)
        prev_date = dates[idx + 1] if idx + 1 < len(dates) else None
        next_date = dates[idx - 1] if idx > 0 else None
    except ValueError:
        prev_date = None
        next_date = None

    return {
        "previous": prev_date,
        "current": date,
        "next": next_date,
    }
