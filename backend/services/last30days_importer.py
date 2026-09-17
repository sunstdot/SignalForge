"""last30days raw v3 JSON → SignalForge content items.

直接读取 last30days skill 通过 `--emit=json` 产出的 raw v3 JSON 报告，
按 schema.Report 结构解析成 content item 列表入库。
"""
import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from services.storage import store_content_items
from services.wingsbot_client import invoke_wingsbot, require_artifact

# raw 平台标记 -> (source_type, 显示名)
# 注意：JSON 里 source 字段用的是 "hackernews"（不是 "hn"），这里做一层归一化
PLATFORM_MAP = {
    "reddit": ("reddit", "Reddit"),
    "x": ("x", "X"),
    "hackernews": ("hn", "Hacker News"),
    "youtube": ("youtube", "YouTube"),
    "tiktok": ("tiktok", "TikTok"),
    "instagram": ("instagram", "Instagram"),
}

# final_score 实测头部约 40-50，归一化到 0-10 用 /5（FEATURED_THRESHOLD=8 对应 final_score>=40）
_SCORE_SCALE = 5.0


def _make_id(platform_key: str, url: str, title: str) -> str:
    basis = url or title
    return f"l30-{platform_key}-{hashlib.md5(basis.encode('utf-8')).hexdigest()[:12]}"


def _normalize_score(value) -> int:
    """把 last30days 的 final_score（实测头部 40-50）归一化到 0-10。"""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    return max(0, min(10, round(v / _SCORE_SCALE)))


def _format_engagement(engagement) -> str:
    """把 engagement dict（{likes, replies, reposts, ...}）格式化成展示字符串。

    例：{"likes": 54, "replies": 9, "reposts": 0} -> "54 likes, 9 replies, 0 reposts"
    如果传入的是字符串（兼容旧格式），原样返回。
    """
    if not engagement:
        return ""
    if isinstance(engagement, str):
        return engagement
    if isinstance(engagement, dict):
        parts = []
        # 按常见字段顺序输出，未识别字段追加在后面
        ordered_keys = ["likes", "replies", "reposts", "upvotes", "points", "views", "comments"]
        seen = set()
        for k in ordered_keys:
            if k in engagement and engagement[k] is not None:
                parts.append(f"{engagement[k]} {k}")
                seen.add(k)
        for k, v in engagement.items():
            if k in seen or v is None:
                continue
            parts.append(f"{v} {k}")
        return ", ".join(parts)
    return str(engagement)


def _sum_engagement(engagement) -> int:
    """把 engagement dict 里所有数值加起来得到 volume。"""
    if not engagement:
        return 0
    if isinstance(engagement, (int, float)):
        return int(engagement)
    if isinstance(engagement, dict):
        total = 0
        for v in engagement.values():
            try:
                total += int(v or 0)
            except (TypeError, ValueError):
                pass
        return total
    # 字符串格式：抽取里面的数字相加
    total = 0
    for n in re.findall(r"[\d,]+", str(engagement)):
        try:
            total += int(n.replace(",", ""))
        except ValueError:
            pass
    return total


def _pick_primary_source_item(candidate: Dict) -> Dict:
    """从 candidate.source_items 里挑一个最能代表该 candidate 的 source item。

    优先选 source 与 candidate.source 一致的；否则取第一个；都没有返回空 dict。
    """
    items = candidate.get("source_items") or []
    if not items:
        return {}
    cand_source = candidate.get("source", "")
    for it in items:
        if it.get("source") == cand_source:
            return it
    return items[0]


def _parse_date(s: Optional[str]) -> str:
    """把 published_at（可能是 ISO 字符串或 'YYYY-MM-DD'）规整成 'YYYY-MM-DD'。"""
    if not s:
        return ""
    s = str(s).strip()
    # 取前 10 位 'YYYY-MM-DD' 部分
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    # 兜底：找 YYYY-MM-DD 模式
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else ""


def parse_last30days_json(text: str) -> List[Dict]:
    """把 last30days skill 的 raw v3 JSON 报告解析成 content item 列表。

    输入是 `last30days.py --emit=json` 产出的 Report JSON 文本，
    schema 对应 .agents/skills/last30days/scripts/lib/schema.py:Report。
    """
    try:
        report = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid last30days JSON: {e}") from e

    if not isinstance(report, dict):
        raise ValueError("last30days JSON 顶层不是 object")

    topic = report.get("topic", "") or ""
    fallback_date = _parse_date(report.get("range_to")) or _parse_date(report.get("range_from"))

    # 用 cluster_id -> (title, score) 建索引，给每个 candidate 补 cluster 元信息
    clusters = report.get("clusters") or []
    cluster_index: Dict[str, Dict] = {c.get("cluster_id", ""): c for c in clusters if isinstance(c, dict)}

    items: List[Dict] = []
    for cand in report.get("ranked_candidates") or []:
        if not isinstance(cand, dict):
            continue
        title = cand.get("title", "") or ""
        url = cand.get("url", "") or ""
        if not title and not url:
            continue

        raw_source = (cand.get("source") or "").lower()
        platform_key, source_name = PLATFORM_MAP.get(raw_source, ("social", raw_source or "unknown"))

        primary = _pick_primary_source_item(cand)
        author = primary.get("author", "") or ""
        engagement = primary.get("engagement") or cand.get("engagement") or {}
        date = _parse_date(primary.get("published_at")) or fallback_date

        cluster = cluster_index.get(cand.get("cluster_id", "")) or {}
        cluster_title = cluster.get("title", "") or ""
        cluster_score_raw = cluster.get("score", 0) or 0
        try:
            cluster_score = int(round(float(cluster_score_raw)))
        except (TypeError, ValueError):
            cluster_score = 0

        score = _normalize_score(cand.get("final_score") or cand.get("rerank_score"))

        snippet = cand.get("snippet", "") or primary.get("body", "") or ""
        body = primary.get("body") or snippet

        items.append({
            "id": _make_id(platform_key, url, title),
            "source": source_name,
            "source_type": platform_key,
            "title": title,
            "url": url,
            "summary": snippet,
            "original_content": body,
            "relevance_score": score,
            "tags": [topic] if topic else [],
            "category": [topic] if topic else [],
            "date": date,
            "created_at": date,
            "metadata": {
                "topic": topic,
                "cluster_id": cand.get("cluster_id", ""),
                "cluster_title": cluster_title,
                "cluster_score": cluster_score,
                "origin": "last30days",
                "author": author,
                "engagement": _format_engagement(engagement),
                "volume": _sum_engagement(engagement),
                "final_score": cand.get("final_score"),
                "rerank_score": cand.get("rerank_score"),
                "candidate_id": cand.get("candidate_id", ""),
                "explanation": cand.get("explanation", ""),
            },
        })

    return items


DEFAULT_L30_DIR = Path.home() / "Documents" / "Last30Days"


def import_last30days_file(path) -> int:
    """解析单个 raw v3 JSON 报告并入库，返回新增条数。"""
    text = Path(path).read_text(encoding="utf-8")
    return store_content_items(parse_last30days_json(text))


def import_last30days_dir(directory=None) -> int:
    """批量导入目录下所有 .json（默认 ~/Documents/Last30Days），返回新增条数。"""
    directory = Path(directory) if directory else DEFAULT_L30_DIR
    total = 0
    for p in sorted(directory.glob("*.json")):
        total += import_last30days_file(p)
    return total


L30_OUTPUT_DIR = DEFAULT_L30_DIR

def run_last30days_via_wingsbot(topic: str) -> int:
    """通过 wingsbot 触发 last30days，再导入产出的最新 JSON 报告，返回新增条数。"""
    json_path = _trigger_wingsbot(topic)
    return import_last30days_file(json_path)


def _build_wingsbot_prompt(topic: str, output_dir: Optional[Path] = None) -> str:
    """构造给 wingsbot agent 的 prompt。

    关键约束：
    - 必须真正调用 last30days skill 工具（Bash 执行 scripts/last30days.py），
      不能凭记忆/常识编一段话回复。
    - last30days skill 默认用 --emit=compact 写 .md 文件；我们要 JSON，
      所以显式要求 --emit=json，skill 会写到 --save-dir 指定目录。
    - SKILL.md 禁止 --emit=md 作为主流程，但 json 是允许的输出格式之一。
    """
    output_dir = output_dir or L30_OUTPUT_DIR
    return (
        f"请调用 last30days 技能研究话题「{topic}」，我需要拿到结构化数据而不是文字总结。\n\n"
        "执行要求：\n"
        "1. 必须真正执行 last30days 脚本（通过 Bash 工具调用 scripts/last30days.py），"
        "不要凭记忆编造结果。如果工具不可用就明确报错，不要伪造「已保存」的回复。\n"
        "2. 多源检索：从 Reddit、X、Hacker News、Web grounding 都要查，"
        "不要只查 X handle。如果话题有人名/品牌/产品名，可以追加 --x-handle，"
        "但 Reddit / Hacker News / Web 不能跳过。\n"
        f"3. 输出格式：用 `--emit=json` 让脚本输出 JSON 报告，用 "
        f"`--save-dir={output_dir}` 把文件写到这个目录。\n"
        "4. 如果某个来源不可用或返回 0 条，在最终回复里写明原因。\n"
        "5. 完成后在回复里给出完整 .json 文件绝对路径。"
    )


def _trigger_wingsbot(topic: str) -> Path:
    start = time.time()
    invocation_dir = L30_OUTPUT_DIR / uuid.uuid4().hex
    invocation_dir.mkdir(parents=True, exist_ok=False)
    prompt = _build_wingsbot_prompt(topic, output_dir=invocation_dir)
    result = invoke_wingsbot(
        prompt,
        session_key=f"signalforge:last30days:{topic}",
        structured=True,
        required_skill="last30days",
        required_tools=["load_skill", "exec"],
        required_artifact_glob=str(invocation_dir / "*.json"),
        artifact_mtime_after=start,
    )
    return require_artifact(result, invocation_dir)
