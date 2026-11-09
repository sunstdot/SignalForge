"""调研 run 的文件存储。

目录结构（data/research/runs/<run_id>/）：
    run.json      本次调研的输入与状态游标
    plan.json     骨架：章节、子问题、实体
    sources/      每个来源一个 JSON（含抓取状态与正文）
    claims.json   原子论断 + 逐字引文
    verify.json   事实簇核验结论
    report.md     成稿
    report.json   结构化产物与覆盖度指标

所有读写都只碰这个目录，与既有功能的数据完全隔离。
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from . import models

RUNS_DIRNAME = "research/runs"


def runs_root() -> Path:
    """动态读取 storage.DATA_DIR，兼容测试里对 DATA_DIR 的 monkeypatch。"""
    import services.storage as storage_module

    return storage_module.DATA_DIR / RUNS_DIRNAME


def run_dir(run_id: str) -> Path:
    return runs_root() / run_id


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


# ───────────────────────── run ─────────────────────────

def create_run(topic: str, questions: List[str], as_of: str) -> models.Run:
    run = models.Run(
        id=new_run_id(),
        topic=topic.strip(),
        questions=[q.strip() for q in questions if q and q.strip()],
        as_of=as_of,
    )
    save_run(run)
    return run


def save_run(run: models.Run) -> None:
    run.updated_at = models._now()
    _write_json(run_dir(run.id) / "run.json", run.as_dict())


def get_run(run_id: str) -> Optional[models.Run]:
    data = _read_json(run_dir(run_id) / "run.json", None)
    if not data:
        return None
    known = {f for f in models.Run.__dataclass_fields__}
    return models.Run(**{k: v for k, v in data.items() if k in known})


def list_runs(limit: int = 100) -> List[dict]:
    root = runs_root()
    if not root.exists():
        return []
    items = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        data = _read_json(path / "run.json", None)
        if data:
            report = _read_json(path / "report.json", None)
            items.append({
                "id": data.get("id"),
                "topic": data.get("topic"),
                "status": data.get("status"),
                "stage": data.get("stage"),
                "as_of": data.get("as_of"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "error": data.get("error", ""),
                "has_report": bool(report),
                "metrics": (report or {}).get("metrics", {}),
            })
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return items[:limit]


def delete_run(run_id: str) -> bool:
    path = run_dir(run_id)
    if not path.exists():
        return False
    shutil.rmtree(path)
    return True


def set_stage(run: models.Run, stage: str, status: str = "") -> models.Run:
    run.stage = stage
    if status:
        run.status = status
    save_run(run)
    return run


# ───────────────────────── plan ─────────────────────────

def save_plan(run_id: str, plan: models.Plan) -> None:
    _write_json(run_dir(run_id) / "plan.json", plan.as_dict())


def get_plan(run_id: str) -> Optional[dict]:
    return _read_json(run_dir(run_id) / "plan.json", None)


# ───────────────────────── sources ─────────────────────────

def _source_path(run_id: str, source_id: str) -> Path:
    return run_dir(run_id) / "sources" / f"{source_id}.json"


def save_source(run_id: str, source: models.Source) -> None:
    _write_json(_source_path(run_id, source.id), source.as_dict())


def get_source(run_id: str, source_id: str) -> Optional[dict]:
    return _read_json(_source_path(run_id, source_id), None)


def list_sources(run_id: str) -> List[dict]:
    directory = run_dir(run_id) / "sources"
    if not directory.exists():
        return []
    return [_read_json(p, {}) for p in sorted(directory.glob("*.json"))]


# ───────────────────────── claims / verify ─────────────────────────

def save_claims(run_id: str, claims: List[models.Claim]) -> None:
    _write_json(run_dir(run_id) / "claims.json", [c.as_dict() for c in claims])


def get_claims(run_id: str) -> List[dict]:
    return _read_json(run_dir(run_id) / "claims.json", [])


def save_verification(run_id: str, verdicts: List[models.Verdict]) -> None:
    _write_json(run_dir(run_id) / "verify.json", [v.as_dict() for v in verdicts])


def get_verification(run_id: str) -> List[dict]:
    return _read_json(run_dir(run_id) / "verify.json", [])


# ───────────────────────── report ─────────────────────────

def save_report(run_id: str, report: models.Report) -> None:
    directory = run_dir(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "report.md").write_text(report.markdown or "", encoding="utf-8")
    _write_json(directory / "report.json", report.as_dict())


def get_report(run_id: str) -> Optional[dict]:
    data = _read_json(run_dir(run_id) / "report.json", None)
    if not data:
        return None
    md_path = run_dir(run_id) / "report.md"
    if md_path.exists():
        data["markdown"] = md_path.read_text(encoding="utf-8")
    return data


# ───────────────────────── 派生视图 ─────────────────────────

def source_lookup(run_id: str) -> Dict[str, dict]:
    return {s["id"]: s for s in list_sources(run_id) if s.get("id")}


def claim_lookup(run_id: str) -> Dict[str, dict]:
    return {c["id"]: c for c in get_claims(run_id) if c.get("id")}


def coverage_metrics(run_id: str) -> Dict[str, object]:
    """成稿之外的覆盖度指标。用来判断这份报告"薄在哪里"，而不是只给一个总分。"""
    sources = list_sources(run_id)
    claims = get_claims(run_id)
    verdicts = get_verification(run_id)
    plan = get_plan(run_id) or {}

    by_tier: Dict[str, int] = {}
    by_fetch: Dict[str, int] = {}
    for source in sources:
        by_tier[source.get("tier", "secondary")] = by_tier.get(source.get("tier", "secondary"), 0) + 1
        by_fetch[source.get("fetch_status", "skipped")] = by_fetch.get(source.get("fetch_status", "skipped"), 0) + 1

    claim_by_verdict = {"confirmed": 0, "single": 0, "conflict": 0}
    for verdict in verdicts:
        key = verdict.get("verdict", "single")
        claim_by_verdict[key] = claim_by_verdict.get(key, 0) + len(verdict.get("claim_ids", []))

    return {
        "sources_total": len(sources),
        "sources_by_tier": by_tier,
        "sources_by_fetch_status": by_fetch,
        "claims_total": len(claims),
        "claims_by_verdict": claim_by_verdict,
        "sub_questions": len(plan.get("sub_questions", [])),
        "sections": len(plan.get("sections", [])),
    }
