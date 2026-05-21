"""Wiki API endpoints"""
import asyncio
from fastapi import APIRouter, HTTPException
from services.storage import (
    get_wiki_concepts,
    get_wiki_article_nodes,
    delete_wiki_concept,
    get_manual_intel_items,
)
import services.wiki_builder as wiki_builder

router = APIRouter()
_background_tasks: set = set()


@router.post("/sync/{item_id}")
async def sync_article(item_id: str):
    task = asyncio.create_task(wiki_builder.process_article(item_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"ok": True, "message": f"Wiki sync started for {item_id}"}


@router.post("/rebuild")
async def rebuild_wiki():
    items = get_manual_intel_items()

    async def _rebuild():
        for item in items:
            await wiki_builder.process_article(item["id"])

    task = asyncio.create_task(_rebuild())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"ok": True, "message": f"Rebuilding wiki for {len(items)} articles"}


@router.get("/status")
async def get_status():
    concepts = get_wiki_concepts()
    nodes = get_wiki_article_nodes()
    last_sync = max((n.get("wiki_synced_at", "") for n in nodes), default=None) if nodes else None
    return {
        "concept_count": len(concepts),
        "article_count": len(nodes),
        "last_synced_at": last_sync,
    }


@router.get("/concepts")
async def list_concepts():
    concepts = get_wiki_concepts()
    return {"concepts": sorted(concepts, key=lambda c: len(c["article_ids"]), reverse=True)}


@router.delete("/concept/{slug}")
async def remove_concept(slug: str):
    ok = delete_wiki_concept(slug)
    if not ok:
        raise HTTPException(status_code=404, detail="Concept not found")
    return {"ok": True}
