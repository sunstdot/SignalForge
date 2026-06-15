"""last30days 实时研究任务 API（后台线程 + 文件持久化任务态）。"""
import threading

from fastapi import APIRouter, HTTPException

from services.last30days_jobs import create_job, finish_job, get_job
from services.last30days_importer import run_last30days_via_wingsbot

router = APIRouter()


def _run_research(job_id: str, topic: str) -> None:
    """在后台线程里跑 last30days（其内部用 asyncio.run，故不能在事件循环里直接调）。"""
    try:
        n = run_last30days_via_wingsbot(topic)
        finish_job(job_id, count=n)
    except Exception as e:  # noqa: BLE001 - 把任何失败写回任务态
        finish_job(job_id, error=str(e)[:500])


@router.post("/research")
async def start_research(request: dict):
    """触发对某关键词的实时 last30days 研究，立即返回 job_id。"""
    topic = (request.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic required")
    job_id = create_job(topic)
    threading.Thread(target=_run_research, args=(job_id, topic), daemon=True).start()
    return {"job_id": job_id, "status": "running", "topic": topic}


@router.get("/research/{job_id}")
async def research_status(job_id: str):
    """查询研究任务状态。"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
