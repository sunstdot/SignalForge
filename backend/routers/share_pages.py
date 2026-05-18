from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.share_page import (
    _load_share_sources,
    build_share_payload,
    render_share_page_html,
)

router = APIRouter()

SHARE_PAGES_DIR = Path(__file__).parent.parent / "docs" / "share-pages"


class GenerateRequest(BaseModel):
    date: str
    signal_ids: List[str]
    opportunity_ids: List[str]


def _filter_opportunities(opportunities: list, opportunity_ids: List[str]) -> list:
    id_set = set(opportunity_ids)
    return [
        item for item in opportunities
        if str(item.get("item_id", "")) in id_set
        or item.get("opportunity_title", "") in id_set
    ]


def _filter_content_items(content_items: list, signal_ids: List[str]) -> list:
    id_set = set(signal_ids)
    return [item for item in content_items if item.get("id") in id_set]


@router.post("/generate")
async def generate_share_page(req: GenerateRequest):
    try:
        opportunities, content_items, quick_reads = _load_share_sources(req.date)

        filtered_opps = _filter_opportunities(opportunities, req.opportunity_ids)
        filtered_items = _filter_content_items(content_items, req.signal_ids)

        payload = build_share_payload(
            req.date, filtered_opps, filtered_items, quick_reads,
            opportunity_limit=99, briefing_limit=99,
        )
        html = render_share_page_html(payload)

        SHARE_PAGES_DIR.mkdir(parents=True, exist_ok=True)
        output_path = SHARE_PAGES_DIR / f"{req.date}.html"
        output_path.write_text(html, encoding="utf-8")

        return {"url": f"/api/share-pages/{req.date}.html"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
