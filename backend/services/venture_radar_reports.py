"""Raw venture-product-radar report storage."""
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from services.storage import DATA_DIR
from services.venture_radar_intelligence import build_quality_metrics, normalize_report


VENTURE_RADAR_DIR = DATA_DIR / "venture_radar"
REPORTS_DIR = VENTURE_RADAR_DIR / "reports"
INDEX_FILE = VENTURE_RADAR_DIR / "index.json"


def _ensure_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> Dict:
    _ensure_dirs()
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return {"reports": []}


def _save_index(index: Dict) -> None:
    _ensure_dirs()
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _report_id_from_path(path: Path) -> str:
    stem = path.stem.strip()
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip("-") or "venture-radar-report"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_source_errors(report: Dict) -> int:
    errors = report.get("errors_by_source") or {}
    if not isinstance(errors, dict):
        return 0
    return sum(len(v) if isinstance(v, list) else 1 for v in errors.values())


def _generated_at(report: Dict, report_id: str) -> str:
    value = str(report.get("generated_at") or "").strip()
    if value:
        return value
    match = re.search(r"(\d{8})T(\d{6})Z", report_id)
    if not match:
        return ""
    date_part, time_part = match.groups()
    return (
        f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        f"T{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}+00:00"
    )


def _week_id(generated_at: str) -> str:
    value = str(generated_at or "").strip()
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _validate_report(report: Dict) -> None:
    if not isinstance(report, dict):
        raise ValueError("venture radar report must be a JSON object")
    schema = str(report.get("schema_version") or "")
    if not schema.startswith("venture-product-radar."):
        raise ValueError("schema_version must start with venture-product-radar.")
    if not str(report.get("topic") or "").strip():
        raise ValueError("topic required")


def summarize_venture_radar_report(report: Dict, report_id: str = "", source_path: str = "") -> Dict:
    generated_at = _generated_at(report, report_id)
    return {
        "id": report_id,
        "topic": report.get("topic", ""),
        "mode": report.get("mode", "radar"),
        "command": report.get("command", ""),
        "generated_at": generated_at,
        "week": _week_id(generated_at),
        "lookback_days": report.get("lookback_days", 0),
        "counts": {
            "companies": len(report.get("companies") or []),
            "products": len(report.get("products") or []),
            "funding_rounds": len(report.get("funding_rounds") or []),
            "signals": len(report.get("signals") or []),
            "source_links": len(report.get("source_links") or []),
            "next_watch_items": len(report.get("next_watch_items") or []),
            "source_errors": _count_source_errors(report),
        },
        "source_path": source_path,
        "imported_at": _now_iso(),
    }


def import_venture_radar_report(path: str) -> Dict:
    source = Path(path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"venture radar report not found: {source}")
    report = json.loads(source.read_text(encoding="utf-8"))
    _validate_report(report)

    _ensure_dirs()
    report_id = _report_id_from_path(source)
    target = REPORTS_DIR / f"{report_id}.json"
    shutil.copyfile(source, target)

    entry = summarize_venture_radar_report(report, report_id=report_id, source_path=str(source))
    index = _load_index()
    existing = [item for item in index.get("reports", []) if item.get("id") != report_id]
    existing.append(entry)
    index["reports"] = sorted(existing, key=lambda item: item.get("generated_at", ""), reverse=True)
    _save_index(index)
    return entry


def list_venture_radar_reports() -> List[Dict]:
    index = _load_index()
    return sorted(index.get("reports", []), key=lambda item: item.get("generated_at", ""), reverse=True)


def list_venture_radar_weeks() -> List[Dict]:
    grouped: Dict[str, Dict] = {}
    for entry in list_venture_radar_reports():
        week = entry.get("week") or _week_id(entry.get("generated_at", ""))
        if not week:
            continue
        bucket = grouped.setdefault(week, {
            "week": week,
            "latest_generated_at": "",
            "report_count": 0,
            "topics": [],
            "counts": {
                "companies": 0,
                "products": 0,
                "funding_rounds": 0,
                "signals": 0,
                "source_links": 0,
                "next_watch_items": 0,
                "source_errors": 0,
            },
        })
        bucket["report_count"] += 1
        bucket["topics"].append(entry.get("topic", ""))
        bucket["latest_generated_at"] = max(bucket["latest_generated_at"], entry.get("generated_at", ""))
        for key in bucket["counts"]:
            bucket["counts"][key] += (entry.get("counts") or {}).get(key, 0)
    weeks = []
    for bucket in grouped.values():
        bucket["topics"] = [topic for topic in bucket["topics"] if topic]
        weeks.append(bucket)
    return sorted(weeks, key=lambda item: item.get("week", ""), reverse=True)


def load_venture_radar_week(week_id: str) -> Optional[Dict]:
    reports = [entry for entry in list_venture_radar_reports() if (entry.get("week") or _week_id(entry.get("generated_at", ""))) == week_id]
    if not reports:
        return None
    aggregate = {
        "products": [],
        "funding_rounds": [],
        "companies": [],
        "signals": [],
        "source_links": [],
        "next_watch_items": [],
        "research_plan": [],
        "intelligence_events": [],
        "intelligence_by_stage": {
            "verified": [],
            "watchlist": [],
            "candidate": [],
            "rejected": [],
        },
        "enrichment_tasks": [],
        "quality_metrics": {},
        "errors_by_source": {},
    }
    for entry in reports:
        report = load_venture_radar_report(entry["id"])
        if not report:
            continue
        aggregate["products"].extend(report.get("products") or [])
        aggregate["funding_rounds"].extend(report.get("funding_rounds") or [])
        aggregate["companies"].extend(report.get("companies") or [])
        aggregate["signals"].extend(report.get("signals") or [])
        aggregate["source_links"].extend(report.get("source_links") or [])
        aggregate["next_watch_items"].extend(report.get("next_watch_items") or [])
        aggregate["research_plan"].extend(report.get("research_plan") or [])
        normalized = normalize_report(report)
        aggregate["intelligence_events"].extend(normalized["events"])
        aggregate["enrichment_tasks"].extend(normalized["enrichment_tasks"])
        for stage, events in normalized["by_stage"].items():
            aggregate["intelligence_by_stage"].setdefault(stage, []).extend(events)
        for source, values in (report.get("errors_by_source") or {}).items():
            aggregate["errors_by_source"].setdefault(source, []).extend(values if isinstance(values, list) else [values])
    aggregate["quality_metrics"] = build_quality_metrics(aggregate["intelligence_events"])
    return {
        "week": week_id,
        "reports": reports,
        "aggregate": aggregate,
    }


def load_venture_radar_report(report_id: str) -> Optional[Dict]:
    safe_id = _report_id_from_path(Path(report_id))
    path = REPORTS_DIR / f"{safe_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
