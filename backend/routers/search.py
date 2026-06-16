"""情报搜索 brief API：搜索 topic → 实时跑 last30days → 聚合+合成 brief（后台 job + 轮询）。"""
import threading

from fastapi import APIRouter, HTTPException

from services.last30days_jobs import create_job, finish_job, get_job
from services.last30days_importer import run_last30days_via_wingsbot
from services.last30days_brief import build_brief

router = APIRouter()


def _run_brief(job_id: str, topic: str) -> None:
    try:
        run_last30days_via_wingsbot(topic)   # 实时抓取并导入到内容库
        brief = build_brief(topic)           # 聚合 + LLM 合成
        finish_job(job_id, count=brief["meta"]["total"], brief=brief)
    except Exception as e:  # noqa: BLE001
        finish_job(job_id, error=str(e)[:500])


@router.post("/brief")
async def start_brief(request: dict):
    """对 topic 触发实时情报简报生成，立即返回 job_id。"""
    topic = (request.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic required")
    job_id = create_job(topic)
    threading.Thread(target=_run_brief, args=(job_id, topic), daemon=True).start()
    return {"job_id": job_id, "status": "running", "topic": topic}


@router.get("/brief/{job_id}")
async def brief_status(job_id: str):
    """查询简报任务状态；done 时 brief 字段为完整简报对象。"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
