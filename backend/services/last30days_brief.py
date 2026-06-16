"""把 last30days 条目聚合 + LLM 合成成前端用的 brief（叙事仪表盘）对象。"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from services.storage import DATA_DIR, get_content_items
from services.llm_client import chat

BRIEFS_DIR = DATA_DIR / "last30days" / "briefs"

FEATURED_THRESHOLD = 8  # relevance_score >= 此值算「精选」

PLATFORM_LABELS = {
    "x": "X", "reddit": "Reddit", "hn": "Hacker News",
    "youtube": "YouTube", "tiktok": "TikTok", "instagram": "Instagram",
}
PLATFORM_UNIT = {"reddit": "↑", "x": "♥", "hn": "pts", "youtube": "views",
                 "tiktok": "views", "instagram": "likes"}
_WEEK = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _fmt_day(date_str: str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.month}月{dt.day:02d}日", _WEEK[dt.weekday()]
    except (ValueError, TypeError):
        return date_str or "未知日期", ""


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "topic").lower()).strip("-") or "topic"


def brief_slug(topic: str) -> str:
    return _slug(topic)


def load_brief(slug: str):
    """从 data/last30days/briefs/<slug>.json 读取已缓存的 brief；不存在返回 None。"""
    p = BRIEFS_DIR / f"{slug}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def aggregate_brief(items: List[Dict], topic: str, took: str = "—") -> Dict:
    """机械聚合：meta / dashboard / voices / caveat / timeline（叙事字段留默认，待合成覆盖）。"""
    total = len(items)
    counts = Counter(i.get("source_type") for i in items)
    vol_by_p: Dict[str, int] = defaultdict(int)
    for i in items:
        vol_by_p[i.get("source_type")] += (i.get("metadata") or {}).get("volume", 0)

    platforms = {p: counts.get(p, 0) for p in ("x", "reddit", "hn")}
    for p, c in counts.items():
        platforms[p] = c

    featured = sum(1 for i in items if i.get("relevance_score", 0) >= FEATURED_THRESHOLD)

    present = [p for p, _ in counts.most_common()]
    tiles = [{
        "p": p, "label": PLATFORM_LABELS.get(p, p.upper()), "n": counts[p],
        "sub": f"{vol_by_p[p]:,} {PLATFORM_UNIT.get(p, '')}".strip(),
    } for p in present[:3]]

    vtotal = sum(vol_by_p.values())
    volume = sorted(
        [{"p": p, "name": PLATFORM_LABELS.get(p, p),
          "pct": round(vol_by_p[p] * 100 / vtotal, 1) if vtotal else 0,
          "raw": f"{vol_by_p[p]:,}"} for p in present],
        key=lambda v: -v["pct"],
    )

    author_vol: Dict[str, int] = defaultdict(int)
    for i in items:
        md = i.get("metadata") or {}
        if md.get("author"):
            author_vol[md["author"]] += md.get("volume", 0)
    voices = [a for a, _ in sorted(author_vol.items(), key=lambda kv: -kv[1])[:6]]

    zero = [PLATFORM_LABELS[p] for p in ("youtube", "tiktok", "instagram") if counts.get(p, 0) == 0]
    caveat = (f"{' / '.join(zero)} 本次返回 0 条 —— 视频侧数据缺失。" if zero
              else "本次各平台均有返回。")

    by_day: Dict[str, List[Dict]] = defaultdict(list)
    for i in items:
        by_day[i.get("date") or ""].append(i)
    timeline = []
    for d in sorted(by_day, reverse=True):
        day, day_note = _fmt_day(d)
        day_items = []
        for i in sorted(by_day[d], key=lambda x: -x.get("relevance_score", 0)):
            md = i.get("metadata") or {}
            day_items.append({
                "id": i.get("id"),
                "p": i.get("source_type"),
                "feat": i.get("relevance_score", 0) >= FEATURED_THRESHOLD,
                "time": "", "ago": "",
                "who": md.get("author") or i.get("source", ""),
                "handle": md.get("author", ""),
                "score": i.get("relevance_score", 0),
                "title": i.get("title", ""),
                "sum": (i.get("summary") or "")[:200],
                "tags": (i.get("tags") or [])[:3],
                "stat": md.get("engagement", ""),
                "reason": "",
                "url": i.get("url", ""),
            })
        timeline.append({"day": day, "dayNote": day_note, "items": day_items})

    return {
        "query": topic, "topic": topic,
        "headline": topic, "kicker": "综合简报 · last30days · 社交独家热点", "lede": "",
        "consensus": {"left": 50, "right": 50, "leftLabel": "", "leftSub": "",
                      "rightLabel": "", "rightSub": ""},
        "meta": {"total": total, "platforms": platforms, "took": took,
                 "window": "近 30 天", "featured": featured},
        "themes": [], "patterns": [], "deepDive": [],
        "dashboard": {"tiles": tiles, "volumeTotal": f"{vtotal:,}", "volume": volume, "insight": ""},
        "voices": voices, "caveat": caveat, "rawNote": "",
        "timeline": timeline,
    }


_SYNTH_KEYS = ("headline", "kicker", "lede", "consensus", "themes", "patterns", "deepDive")


def synthesize_narrative(items: List[Dict], topic: str) -> Dict:
    """LLM 合成叙事字段；解析失败返回 {} 让上层降级。"""
    top = sorted(items, key=lambda x: -x.get("relevance_score", 0))[:30]
    lines = []
    for i in top:
        md = i.get("metadata") or {}
        lines.append(
            f"[{i.get('id')}] ({i.get('source_type')} · {md.get('author','')} · score {i.get('relevance_score',0)}) "
            f"{i.get('title','')} — {(i.get('summary') or '')[:160]}"
        )
    context = "\n".join(lines)
    prompt = f"""你是情报分析师。基于以下「{topic}」最近 30 天的多平台帖子，产出一份中文综合简报。
严格输出 JSON（不要 markdown 代码块），结构：
{{
  "headline": "一句话主标题（可含中文逗号，逗号后半句会被高亮）",
  "kicker": "一行 kicker，如 '综合简报 · 本周主线'",
  "lede": "2-3 句导语，可用 {{b}}...{{/b}} 加粗",
  "consensus": {{"left": 数字, "right": 100-left, "leftLabel":"正方标签","leftSub":"小字","rightLabel":"反方标签","rightSub":"小字"}},
  "themes": [{{"n":"01","title":"小标题","html":"正文，可用 <q>引用</q> <src>@来源</src> <num>数字</num> <hl>高亮</hl>"}} ...3-4 条],
  "patterns": [{{"n":1,"text":"关键模式","src":"@来源","lead":true}} ...4-5 条，仅第一条 lead:true],
  "deepDive": [{{"k":"A","q":"可深入的问题","a":"答案，可用 <b>加粗</b> <c>代码</c> <br>"}} ...3 条],
  "insight": "一句平台分布洞察，可用 <b>..</b>",
  "reasons": {{"<帖子id>":"该帖入选的推荐理由（1 句）", ...只给 score>=8 的帖子}}
}}

帖子：
{context}
"""
    try:
        raw = chat([{"role": "user", "content": prompt}]).strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        text = m.group(0) if m else raw
        # 容忍 LLM 常见的非严格 JSON：去掉对象/数组结尾多余的逗号
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception as e:  # noqa: BLE001
        print(f"[brief] synthesize failed: {e}")
        return {}


def _load_topic_items(topic: str) -> List[Dict]:
    """从内容库取该 topic 的 last30days 条目。"""
    items = get_content_items(limit=500)
    t = (topic or "").strip().lower()
    out = []
    for i in items:
        md = i.get("metadata") or {}
        if md.get("origin") != "last30days":
            continue
        hay = " ".join(filter(None, [md.get("topic", ""), i.get("title", ""),
                                     " ".join(i.get("tags") or [])])).lower()
        if not t or t in hay or t in (md.get("topic", "") or "").lower():
            out.append(i)
    return out


def build_brief(topic: str, persist: bool = True) -> Dict:
    """聚合 + 合成 → 完整 brief；可选落盘。"""
    items = _load_topic_items(topic)
    brief = aggregate_brief(items, topic)
    narrative = synthesize_narrative(items, topic) if items else {}

    for k in _SYNTH_KEYS:
        if narrative.get(k):
            brief[k] = narrative[k]
    if narrative.get("insight"):
        brief["dashboard"]["insight"] = narrative["insight"]
    reasons = narrative.get("reasons") or {}
    for group in brief["timeline"]:
        for it in group["items"]:
            it["reason"] = reasons.get(it.get("id"), it.get("reason", ""))

    if persist:
        BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
        (BRIEFS_DIR / f"{_slug(topic)}.json").write_text(
            json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    return brief
