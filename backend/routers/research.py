"""深度调研 API。

全部路由挂在 /api/research 下，数据落在 data/research/，与既有功能互不影响。
"""
from __future__ import annotations

import asyncio
import threading
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from services import research
from services.research import store

router = APIRouter()

_run_lock = threading.Lock()
_running: set[str] = set()


class CreateRunRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    questions: List[str] = Field(default_factory=list)
    as_of: Optional[str] = None


def _execute(run_id: str) -> None:
    """后台执行一个 run。用独立线程跑 asyncio，避免和 FastAPI 事件循环打架。"""
    with _run_lock:
        if run_id in _running:
            return
        _running.add(run_id)
    try:
        asyncio.run(research.ResearchPipeline(store.get_run(run_id)).run_all())
    except Exception:
        pass  # 失败状态已由 pipeline 写入 run.json
    finally:
        with _run_lock:
            _running.discard(run_id)


def _execute_stage(run_id: str, stage: str) -> None:
    """从指定阶段续跑。来源与论断已在盘上，不重新抓取和抽取。"""
    with _run_lock:
        if run_id in _running:
            return
        _running.add(run_id)
    try:
        asyncio.run(research.ResearchPipeline(store.get_run(run_id)).run_from(stage))
    except Exception:
        pass
    finally:
        with _run_lock:
            _running.discard(run_id)


@router.get("/status")
async def status():
    """当前搜索后端是否降级，以及有哪些 run 正在跑。"""
    info = research.backend_status()
    info["running"] = sorted(_running)
    return info


@router.get("/runs")
async def list_runs(limit: int = 50):
    return {"runs": store.list_runs(limit=limit)}


@router.post("/runs", status_code=201)
async def create_run(body: CreateRunRequest, background: BackgroundTasks):
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic 不能为空")
    run = store.create_run(topic, body.questions, body.as_of or date.today().isoformat())
    background.add_task(_execute, run.id)
    return {"run": run.as_dict()}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run": run.as_dict(), "plan": store.get_plan(run_id)}


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str):
    if not store.get_run(run_id):
        raise HTTPException(status_code=404, detail="run not found")
    report = store.get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not ready")
    # 以成稿时写入的指标为准，实时覆盖度作为补充，便于看数据后来有没有变化。
    metrics = dict(report.get("metrics") or {})
    metrics.update(store.coverage_metrics(run_id))
    return {
        "report": report,
        "metrics": metrics,
    }


@router.get("/runs/{run_id}/sources")
async def get_sources(run_id: str):
    if not store.get_run(run_id):
        raise HTTPException(status_code=404, detail="run not found")
    sources = store.list_sources(run_id)
    return {
        "sources": [
            {
                "id": s.get("id"),
                "url": s.get("url"),
                "title": s.get("title"),
                "tier": s.get("tier"),
                "fetch_status": s.get("fetch_status"),
                "fetch_detail": s.get("fetch_detail"),
                "published": s.get("published"),
                "chars": len(s.get("text") or ""),
            }
            for s in sources
        ]
    }


@router.get("/runs/{run_id}/claims")
async def get_claims(run_id: str, verdict: Optional[str] = None):
    """论断列表。verdict 可选 confirmed / single / conflict，用于前端过滤。"""
    if not store.get_run(run_id):
        raise HTTPException(status_code=404, detail="run not found")
    claims = {c["id"]: c for c in store.get_claims(run_id)}
    verdict_map = {}
    for item in store.get_verification(run_id):
        for cid in item.get("claim_ids", []):
            verdict_map[cid] = item.get("verdict", "single")

    rows = []
    for cid, claim in claims.items():
        row = dict(claim)
        row["verdict"] = verdict_map.get(cid, "single")
        if verdict and row["verdict"] != verdict:
            continue
        rows.append(row)
    rows.sort(key=lambda r: r["id"])
    return {"claims": rows}


@router.post("/runs/{run_id}/reverify")
async def reverify(run_id: str, background: BackgroundTasks):
    """只重跑核验与成稿，不动已抓到的来源和已抽出的论断。

    核验逻辑或 prompt 调整后，用它给已有 run 补跑，避免把几十次抓取和
    抽取的额度再花一遍。
    """
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    if not store.get_claims(run_id):
        raise HTTPException(status_code=400, detail="该 run 还没有论断，无法只重跑核验")

    background.add_task(_execute_stage, run_id, "verify")
    return {"run": run.as_dict(), "stage": "verify"}


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    if not store.delete_run(run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return {"deleted": True}
