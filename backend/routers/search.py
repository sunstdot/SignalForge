"""情报搜索 brief API：搜索 topic → 实时跑 last30days → 聚合+合成 brief（后台 job + 轮询）。

brief 数据落在 data/last30days/briefs/<slug>.json；job 表只存 slug 引用，不内嵌整份 brief。
"""
import threading

from fastapi import APIRouter, HTTPException

from services.last30days_jobs import create_job, finish_job, get_job
from services.last30days_importer import run_last30days_via_wingsbot
from services.last30days_brief import build_brief, brief_slug, load_brief, load_history

router = APIRouter()


def _run_brief(job_id: str, topic: str) -> None:
    try:
        run_last30days_via_wingsbot(topic)        # 实时抓取并导入到内容库
        brief = build_brief(topic)                # 聚合 + LLM 合成 + 落盘到 briefs/<slug>.json
        finish_job(job_id, count=brief["meta"]["total"], brief_slug=brief_slug(topic))
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


@router.get("/history")
async def search_history():
    """返回搜索记录（最近在前），点击可读取对应的缓存 brief。"""
    return {"history": load_history()}


@router.get("/brief")
async def cached_brief(topic: str):
    """直接读取某 topic 已缓存的 brief 文件（用于刷新后恢复，不重新抓取）。"""
    brief = load_brief(brief_slug(topic))
    if brief is None:
        raise HTTPException(status_code=404, detail="no cached brief")
    return brief


@router.get("/brief/{job_id}")
async def brief_status(job_id: str):
    """查询简报任务状态；done 时从 briefs/<slug>.json 读出 brief 一并返回。"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") == "done" and job.get("brief_slug"):
        return {**job, "brief": load_brief(job["brief_slug"])}
    return job
