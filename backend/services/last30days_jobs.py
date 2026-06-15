"""last30days 实时研究任务的文件持久化存储（进程内内存 + data/last30days/jobs.json）。"""
import json
import threading
import uuid
from datetime import datetime
from typing import Dict, Optional

from services.storage import DATA_DIR

JOBS_DIR = DATA_DIR / "last30days"
JOBS_FILE = JOBS_DIR / "jobs.json"

_LOCK = threading.Lock()


def _load() -> Dict:
    if JOBS_FILE.exists():
        return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    return {}


def _save(jobs: Dict) -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def create_job(topic: str) -> str:
    """登记一个 running 任务，返回 job_id。"""
    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        jobs = _load()
        jobs[job_id] = {
            "job_id": job_id,
            "topic": topic,
            "status": "running",
            "count": None,
            "error": None,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": None,
        }
        _save(jobs)
    return job_id


def finish_job(job_id: str, *, count: Optional[int] = None, error: Optional[str] = None) -> None:
    """标记任务结束：error 非空 → status=error，否则 status=done。"""
    with _LOCK:
        jobs = _load()
        job = jobs.get(job_id)
        if not job:
            return
        job["status"] = "error" if error else "done"
        job["count"] = count
        job["error"] = error
        job["finished_at"] = datetime.now().isoformat(timespec="seconds")
        _save(jobs)


def get_job(job_id: str) -> Optional[Dict]:
    with _LOCK:
        return _load().get(job_id)
