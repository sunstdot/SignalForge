"""Run venture-product-radar and archive its JSON reports."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from services.venture_radar_intelligence import normalize_report
from services.venture_radar_reports import import_venture_radar_report
from services.wingsbot_client import invoke_wingsbot, require_artifact


DEFAULT_VPR_DIR = Path.home() / "Documents" / "VentureProductRadar"
VPR_OUTPUT_DIR = DEFAULT_VPR_DIR
_INVOCATION_DIR_PREFIX = "signalforge-invoke-"
VPR_SKILL_DIR = Path("/Users/shitaosun/Project/AI-Personal/wingsbot/wingsbot/skills/venture-product-radar")
DEFAULT_WEEKLY_TOPIC = "AI venture funding product launches startup signals"
MODE_COMMANDS = {
    "radar": "venture-radar",
    "vc": "venture-vc",
    "product": "venture-product",
    "finance": "venture-finance",
}
MODE_DEFAULT_SOURCES = {
    "radar": ["web", "producthunt", "funding", "vc"],
    "vc": ["web", "vc", "funding"],
    "product": ["web", "producthunt"],
    "finance": ["web", "funding", "vc"],
}


def _make_id(kind: str, title: str, url: str = "") -> str:
    basis = url or title
    return f"vpr-{kind}-{hashlib.md5(basis.encode('utf-8')).hexdigest()[:12]}"


def _parse_date(value: Optional[str], fallback: str = "") -> str:
    if not value:
        return fallback
    value = str(value).strip()
    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        return value[:10]
    m = re.search(r"(\d{4}-\d{2}-\d{2})", value)
    return m.group(1) if m else fallback


def _confidence_score(confidence: str) -> int:
    return {
        "high": 8,
        "medium": 5,
        "low": 3,
    }.get((confidence or "").lower(), 5)


def _field_value(field):
    if isinstance(field, dict) and "value" in field:
        return field.get("value")
    return field


def _base_item(
    *,
    kind: str,
    source_type: str,
    source: str,
    title: str,
    url: str,
    summary: str,
    topic: str,
    command: str,
    mode: str,
    date: str,
    score: int,
    metadata: Dict,
) -> Dict:
    return {
        "id": _make_id(kind, title, url),
        "source": source,
        "source_type": source_type,
        "title": title,
        "url": url,
        "summary": summary,
        "original_content": summary,
        "relevance_score": score,
        "tags": [topic] if topic else [],
        "category": [topic] if topic else [],
        "date": date,
        "created_at": date,
        "metadata": {
            "origin": "venture-product-radar",
            "topic": topic,
            "command": command,
            "mode": mode,
            **metadata,
        },
    }


def parse_venture_product_radar_json(text: str) -> List[Dict]:
    try:
        report = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid venture-product-radar JSON: {e}") from e

    if not isinstance(report, dict):
        raise ValueError("venture-product-radar JSON top-level value is not an object")

    topic = report.get("topic", "") or ""
    mode = _normalize_mode(report.get("mode"))
    command = report.get("command") or MODE_COMMANDS[mode]
    fallback_date = _parse_date(report.get("generated_at")) or time.strftime("%Y-%m-%d")
    normalized = normalize_report(report)
    items: List[Dict] = []

    for company in report.get("companies") or []:
        if not isinstance(company, dict):
            continue
        name = company.get("name", "") or ""
        if not name:
            continue
        url = company.get("website", "") or ""
        summary = company.get("description", "") or ""
        confidence = company.get("confidence", "")
        items.append(_base_item(
            kind="company",
            source_type="vc_company",
            source="Venture Product Radar",
            title=name,
            url=url,
            summary=summary,
            topic=topic,
            command=command,
            mode=mode,
            date=fallback_date,
            score=_confidence_score(confidence),
            metadata={
                "entity_type": "company",
                "sector": company.get("sector", ""),
                "stage": company.get("stage", ""),
                "investors": company.get("investors") or [],
                "why_it_matters": company.get("why_it_matters", ""),
                "opportunity_angle": company.get("opportunity_angle", ""),
                "evidence_gaps": company.get("evidence_gaps") or [],
                "confidence": confidence,
                "source_urls": company.get("source_urls") or [],
            },
        ))

    for product in report.get("products") or []:
        if not isinstance(product, dict):
            continue
        name = product.get("name", "") or ""
        if not name:
            continue
        platform = product.get("platform", "") or ""
        source = platform if platform else "Venture Product Radar"
        url = product.get("url", "") or product.get("github_url", "") or _first_url(product.get("source_urls"))
        summary = product.get("tagline", "") or product.get("description", "") or ""
        confidence = product.get("confidence", "")
        date = _parse_date(product.get("launch_date"), fallback_date)
        items.append(_base_item(
            kind="product",
            source_type="product",
            source=source,
            title=name,
            url=url,
            summary=summary,
            topic=topic,
            command=command,
            mode=mode,
            date=date,
            score=_confidence_score(confidence),
            metadata={
                "entity_type": "product",
                "pipeline_stage": "verified",
                "company": product.get("company", ""),
                "platform": platform,
                "why_it_matters": product.get("why_it_matters", ""),
                "opportunity_angle": product.get("opportunity_angle", ""),
                "evidence_gaps": product.get("evidence_gaps") or [],
                "confidence": confidence,
                "source_urls": product.get("source_urls") or [],
            },
        ))

    for funding in normalized["events"]:
        if funding.get("entity_type") != "funding_event" or funding.get("pipeline_stage") != "verified":
            continue
        company = funding.get("company_name", "") or ""
        if not company:
            continue
        round_type = _field_value(funding.get("round")) or "Funding"
        title = funding.get("title_zh") or funding.get("title") or f"{company} {round_type} funding"
        amount = _field_value(funding.get("amount_raised")) or ""
        valuation = _field_value(funding.get("valuation")) or ""
        investors = _field_value(funding.get("lead_investors")) or []
        summary_parts = [part for part in [amount, valuation, round_type, ", ".join(investors)] if part]
        summary = funding.get("what_happened") or " - ".join(summary_parts)
        confidence = funding.get("confidence", "")
        url = _first_url(funding.get("source_urls"))
        event_date = (
            _field_value(funding.get("announced_date"))
            or _field_value(funding.get("closed_date"))
            or _field_value(funding.get("filed_date"))
            or _field_value(funding.get("published_date"))
        )
        date = _parse_date(event_date, fallback_date)
        items.append(_base_item(
            kind="funding",
            source_type="funding",
            source="Venture Product Radar",
            title=title,
            url=url,
            summary=summary,
            topic=topic,
            command=command,
            mode=mode,
            date=date,
            score=_confidence_score(confidence),
            metadata={
                "entity_type": "funding_event",
                "pipeline_stage": funding.get("pipeline_stage"),
                "company": company,
                "event_status": funding.get("event_status"),
                "round": funding.get("round"),
                "amount_raised": funding.get("amount_raised"),
                "valuation": funding.get("valuation"),
                "valuation_type": funding.get("valuation_type"),
                "announced_date": funding.get("announced_date"),
                "lead_investors": funding.get("lead_investors"),
                "participating_investors": funding.get("participating_investors"),
                "why_it_matters": funding.get("why_it_matters", ""),
                "opportunity_angle": funding.get("opportunity_angle", ""),
                "evidence_gaps": funding.get("evidence_gaps") or [],
                "evidence_conflicts": funding.get("evidence_conflicts") or [],
                "evidence_score": funding.get("evidence_score", 0),
                "completeness_score": funding.get("completeness_score", 0),
                "confidence": confidence,
                "source_urls": funding.get("source_urls") or [],
            },
        ))

    for signal in report.get("signals") or []:
        if not isinstance(signal, dict) or signal.get("type") == "research_plan":
            continue
        title = signal.get("title", "") or ""
        if not title:
            continue
        confidence = signal.get("confidence", "")
        url = signal.get("url", "") or _first_url(signal.get("source_urls"))
        summary = signal.get("summary", "") or ""
        items.append(_base_item(
            kind="signal",
            source_type="venture_signal",
            source="Venture Product Radar",
            title=title,
            url=url,
            summary=summary,
            topic=topic,
            command=command,
            mode=mode,
            date=fallback_date,
            score=_confidence_score(confidence),
            metadata={
                "entity_type": "signal",
                "signal_type": signal.get("type", "") or signal.get("signal_type", ""),
                "signal_score": signal.get("signal_score", ""),
                "signal_strength": signal.get("signal_strength", ""),
                "why_it_matters": signal.get("why_it_matters", ""),
                "opportunity_angle": signal.get("opportunity_angle", ""),
                "evidence_gaps": signal.get("evidence_gaps") or [],
                "confidence": confidence,
                "source_urls": signal.get("source_urls") or ([url] if url else []),
            },
        ))

    return items


def _first_url(urls) -> str:
    if isinstance(urls, list) and urls:
        return str(urls[0] or "")
    return ""


def import_venture_product_radar_file(path) -> Dict:
    return import_venture_radar_report(path)


def _cleanup_invocation_dir(path: Path) -> None:
    path = Path(path)
    base = VPR_OUTPUT_DIR.resolve()
    resolved = path.resolve()
    if resolved.parent == base and resolved.name.startswith(_INVOCATION_DIR_PREFIX):
        shutil.rmtree(resolved, ignore_errors=True)


def run_venture_product_radar_via_wingsbot(
    topic: str,
    sources: Optional[List[str]] = None,
    mode: str = "radar",
) -> int:
    json_path = _trigger_wingsbot(topic, sources=sources, mode=mode)
    try:
        import_venture_product_radar_file(json_path)
        return 1
    finally:
        _cleanup_invocation_dir(json_path.parent)


def build_direct_venture_radar_command(
    *,
    mode: str = "radar",
    sources: str = "all",
    lookback_days: int = 7,
    max_items: int = 30,
    output_dir: Path = VPR_OUTPUT_DIR,
) -> List[str]:
    selected_mode = _normalize_mode(mode)
    script_path = VPR_SKILL_DIR / "scripts" / "venture_product_radar.py"
    return [
        sys.executable,
        str(script_path),
        "--mode",
        selected_mode,
        "--topic",
        DEFAULT_WEEKLY_TOPIC,
        "--sources",
        sources,
        "--lookback-days",
        str(lookback_days),
        "--emit",
        "json",
        "--output-dir",
        str(output_dir),
        "--max-items",
        str(max_items),
    ]


def _report_path_from_stdout(stdout: str) -> Path:
    lines = [line.strip() for line in (stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("venture-product-radar did not print a JSON report path")
    path = Path(lines[-1]).expanduser()
    if not path.exists():
        raise RuntimeError(f"venture-product-radar report path does not exist: {path}")
    return path


def run_venture_product_radar_direct(
    *,
    mode: str = "radar",
    sources: str = "all",
    lookback_days: int = 7,
    max_items: int = 30,
    output_dir: Path = VPR_OUTPUT_DIR,
) -> Dict:
    command = build_direct_venture_radar_command(
        mode=mode,
        sources=sources,
        lookback_days=lookback_days,
        max_items=max_items,
        output_dir=output_dir,
    )
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    report_path = _report_path_from_stdout(completed.stdout)
    archive = import_venture_product_radar_file(report_path)
    return {
        "report_path": str(report_path),
        "reports_archived": 1,
        "archive": archive,
    }


def _normalize_sources(sources: Optional[List[str]], mode: str = "radar") -> List[str]:
    allowed = {"web", "producthunt", "funding", "vc"}
    if not sources:
        return MODE_DEFAULT_SOURCES[_normalize_mode(mode)]
    clean = []
    for source in sources:
        value = str(source).strip().lower()
        if value in allowed and value not in clean:
            clean.append(value)
    return clean or MODE_DEFAULT_SOURCES[_normalize_mode(mode)]


def _normalize_mode(mode: Optional[str]) -> str:
    value = (mode or "radar").strip().lower()
    return value if value in MODE_COMMANDS else "radar"


def _build_wingsbot_prompt(
    topic: str,
    sources: Optional[List[str]] = None,
    mode: str = "radar",
    output_dir: Optional[Path] = None,
) -> str:
    selected_mode = _normalize_mode(mode)
    selected = _normalize_sources(sources, selected_mode)
    command = MODE_COMMANDS[selected_mode]
    source_arg = ",".join(selected)
    output_dir = output_dir or VPR_OUTPUT_DIR
    script_path = VPR_SKILL_DIR / "scripts" / "venture_product_radar.py"
    return (
        f"请调用 venture-product-radar 技能，以 /{command} 模式研究话题「{topic}」，"
        "输出给 SignalForge 导入的 JSON。\n\n"
        "执行要求：\n"
        "1. 必须真正加载并使用 venture-product-radar skill；如果 load_skill 可用，先调用 "
        "`load_skill(\"venture-product-radar\")`。\n"
        "2. 先按该 command 的 scout 维度执行 WebSearch，收集可验证来源；不要凭记忆编造公司、产品或融资信息。\n"
        f"3. 再通过 Bash 执行脚本生成 scaffold：`python3 {script_path} --mode {selected_mode} --topic \"{topic}\" "
        f"--sources {source_arg} --emit json --output-dir {output_dir}`。\n"
        "4. 根据 WebSearch 证据改写 scaffold JSON 并保存为新的最终 JSON；"
        "不要只返回只有 research_plan 的空 scaffold，除非搜索后确实没有可验证结果。\n"
        "5. JSON 中每条公司、产品、融资或信号都要尽量包含 why_it_matters、"
        "opportunity_angle、confidence、source_urls/evidence_gaps。\n"
        "6. 对融资事件使用严格 contract：pipeline_stage(candidate/watchlist/verified/rejected)、"
        "event_status(rumor/in_talks/filed/announced/closed/cancelled/unclear)、"
        "amount_raised、valuation、valuation_type、currency、round、published_date、"
        "announced_date、filed_date、closed_date。禁止把 valuation 写入 amount_raised，"
        "禁止把新闻 published_date 当 announced_date。\n"
        "7. 关键字段要带 provenance：value、source_urls、source_types、confidence；"
        "至少覆盖 amount_raised、valuation、round、event_status、announced_date、"
        "lead_investors、participating_investors。补充 source_count、official_source_count、"
        "independent_source_count、evidence_score、completeness_score、evidence_conflicts。\n"
        "8. 对每条候选生成 enrichment_tasks，格式为 {entity, field_to_verify, query, "
        "expected_source_type, priority}，任务必须指向具体字段和期望来源类型；逐项执行可执行任务，"
        "把找到的证据回填到字段 provenance，无法完成的任务保留为 evidence_gaps。\n"
        "9. 分析字段使用 what_happened、what_changed、why_it_matters、market_implication、"
        "opportunity_angle、risk_and_uncertainty、next_watch_items；证据不足时明确写"
        "「当前证据不足，尚不能判断其市场意义。」不要输出空洞模板。\n"
        "10. title_zh 必须是完整、不截断的中文标题。产品发布采用轻量准入：发现明确的新产品发布即可进入 verified，"
        "不套用融资的双来源门槛。\n"
        "11. 完成后在回复里给出完整 .json 文件绝对路径。\n"
        "12. 如果工具或网络不可用，返回真实错误，不要伪造已保存结果。"
    )


def _trigger_wingsbot(topic: str, sources: Optional[List[str]] = None, mode: str = "radar") -> Path:
    start = time.time()
    selected_mode = _normalize_mode(mode)
    invocation_dir = VPR_OUTPUT_DIR / f"{_INVOCATION_DIR_PREFIX}{uuid.uuid4().hex}"
    invocation_dir.mkdir(parents=True, exist_ok=False)
    try:
        prompt = _build_wingsbot_prompt(
            topic, sources=sources, mode=mode, output_dir=invocation_dir
        )
        result = invoke_wingsbot(
            prompt,
            session_key=f"signalforge:venture-product-radar:{selected_mode}:{topic}",
            structured=True,
            required_skill="venture-product-radar",
            required_tools=["load_skill", "exec"],
            required_artifact_glob=str(invocation_dir / "*.json"),
            artifact_mtime_after=start,
        )
        return require_artifact(result, invocation_dir)
    except Exception:
        _cleanup_invocation_dir(invocation_dir)
        raise
