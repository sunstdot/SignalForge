"""venture-product-radar research task API."""
import threading

from fastapi import APIRouter, HTTPException

from services.last30days_jobs import create_job, finish_job, get_job
from services.venture_radar_reports import (
    import_venture_radar_report,
    list_venture_radar_weeks,
    list_venture_radar_reports,
    load_venture_radar_week,
    load_venture_radar_report,
)
from services.venture_product_radar_importer import run_venture_product_radar_via_wingsbot

router = APIRouter()


def _normalize_sources(raw):
    if not isinstance(raw, list):
        return None
    sources = [str(item).strip().lower() for item in raw if str(item).strip()]
    return sources or None


def _run_research(job_id: str, topic: str, sources, mode: str = "radar") -> None:
    try:
        n = run_venture_product_radar_via_wingsbot(topic, sources=sources, mode=mode)
        finish_job(job_id, count=n)
    except Exception as e:  # noqa: BLE001 - persist background task failure
        finish_job(job_id, error=str(e)[:500])


def _start_research_job(request: dict, mode: str):
    topic = (request.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic required")
    sources = _normalize_sources(request.get("sources"))
    job_id = create_job(topic)
    threading.Thread(target=_run_research, args=(job_id, topic, sources, mode), daemon=True).start()
    return {"job_id": job_id, "status": "running", "topic": topic}


@router.post("/research")
async def start_research(request: dict):
    mode = (request.get("mode") or "radar").strip().lower()
    if mode not in {"radar", "vc", "product", "finance"}:
        mode = "radar"
    return _start_research_job(request, mode)


@router.post("/vc")
async def start_vc_research(request: dict):
    return _start_research_job(request, "vc")


@router.post("/product")
async def start_product_research(request: dict):
    return _start_research_job(request, "product")


@router.post("/finance")
async def start_finance_research(request: dict):
    return _start_research_job(request, "finance")


@router.get("/reports")
async def reports_index():
    return {"reports": list_venture_radar_reports()}


@router.get("/weeks")
async def weeks_index():
    return {"weeks": list_venture_radar_weeks()}


@router.get("/weeks/{week_id}")
async def week_detail(week_id: str):
    week = load_venture_radar_week(week_id)
    if not week:
        raise HTTPException(status_code=404, detail="week not found")
    return week


@router.get("/reports/{report_id}")
async def report_detail(report_id: str):
    report = load_venture_radar_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    return report


@router.post("/import-file")
async def import_report_file(request: dict):
    path = (request.get("path") or "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="path required")
    try:
        return import_venture_radar_report(path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/research/{job_id}")
async def research_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
