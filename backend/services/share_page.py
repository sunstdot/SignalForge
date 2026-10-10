import json
import re
from html import escape
from pathlib import Path
from typing import Dict, List

from .storage import CONTENT_DIR, load_quick_reads


def build_share_payload(
    date: str,
    opportunities: List[Dict],
    content_items: List[Dict],
    quick_reads: Dict[str, str],
    opportunity_limit: int = 3,
    briefing_limit: int = 5,
) -> Dict:
    ranked_opportunities = sorted(
        opportunities,
        key=lambda item: item.get("total_score", 0),
        reverse=True,
    )[:opportunity_limit]

    normalized_opportunities = [
        {
            "title": item.get("opportunity_title") or item.get("title") or "未命名商业机会",
            "score": item.get("total_score", 0),
            "core_insight": item.get("core_insight", ""),
            "product_form": item.get("product_form", ""),
            "business_model": item.get("business_model", ""),
            "target_users": item.get("target_users", ""),
            "mvp_features": item.get("mvp_features", []),
            "risks": item.get("risks", ""),
        }
        for item in ranked_opportunities
    ]

    ranked_items = sorted(
        (item for item in content_items if item.get("id") in quick_reads),
        key=lambda item: item.get("relevance_score", 0),
        reverse=True,
    )
    selected_items = _select_diverse_items(ranked_items, briefing_limit)
    normalized_briefings = [
        {
            "id": item["id"],
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "source_type": item.get("source_type", "news"),
            "quick_read": quick_reads[item["id"]],
        }
        for item in selected_items
    ]

    return {
        "date": date,
        "opportunities": normalized_opportunities,
        "briefings": normalized_briefings,
    }


def _render_opportunity_card(index: int, item: Dict) -> str:
    mvp_items = "".join(
        f"<li>{escape(f)}</li>" for f in item.get("mvp_features", [])
    )
    mvp_section = f'<ul class="opp-mvp">{mvp_items}</ul>' if mvp_items else ""

    rows = []
    if item.get("core_insight"):
        rows.append(f'<div class="opp-row"><span class="opp-label">触发洞察</span><p>{escape(item["core_insight"])}</p></div>')
    if item.get("product_form"):
        rows.append(f'<div class="opp-row"><span class="opp-label">应用场景</span><p>{escape(item["product_form"])}</p></div>')
    if item.get("business_model"):
        rows.append(f'<div class="opp-row"><span class="opp-label">商业模式</span><p>{escape(item["business_model"])}</p></div>')
    if mvp_section:
        rows.append(f'<div class="opp-row"><span class="opp-label">MVP 功能</span>{mvp_section}</div>')
    if item.get("risks"):
        rows.append(f'<div class="opp-row"><span class="opp-label">潜在风险</span><p>{escape(item["risks"])}</p></div>')

    return f"""
        <article class="xhs-item opp-card">
          <div class="xhs-headline">
            <span class="xhs-rank">{index}</span>
            <h4>{escape(item["title"])}</h4>
            <span class="xhs-score">{item["score"]} / 20</span>
          </div>
          <div class="opp-body">{"".join(rows)}</div>
        </article>
        """


def _select_diverse_items(items: List[Dict], limit: int) -> List[Dict]:
    selected = []
    selected_ids = set()
    selected_types = set()

    if items:
        selected.append(items[0])
        selected_ids.add(items[0]["id"])
        selected_types.add(_briefing_type(items[0]))

    for item in items:
        item_type = _briefing_type(item)
        if item["id"] in selected_ids or item_type in selected_types:
            continue
        selected.append(item)
        selected_ids.add(item["id"])
        selected_types.add(item_type)
        if len(selected) >= limit:
            return selected

    for item in items:
        if item["id"] in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(item["id"])
        if len(selected) >= limit:
            break

    return selected


def _briefing_type(item: Dict) -> str:
    if item.get("source_type") == "hackernews" or item.get("source") == "HackerNews Daily":
        return "hackernews"
    return item.get("source_type", "news")


def render_share_page_html(payload: Dict) -> str:
    opportunities = payload["opportunities"]
    briefings = payload["briefings"]
    briefing_pages = [briefings[:3], briefings[3:5]]

    opportunity_cards = "".join(
        _render_opportunity_card(index, item)
        for index, item in enumerate(opportunities, 1)
    )

    briefing_sections = "".join(
        _render_briefing_page(page_items, page_index)
        for page_index, page_items in enumerate(briefing_pages, start=1)
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>SignalForge Xiaohongshu Share</title>
  <style>{_SHARE_PAGE_CSS}</style>
</head>
<body>
  <main class="xhs-stage">
    <section class="xhs-page">
      <div class="xhs-kicker">Page 1 / Business</div>
      <h1>今天最值得看的 3 个 AI 商业机会</h1>
      <div class="xhs-list">{opportunity_cards}</div>
      <footer><span>SignalForge</span><span>{escape(payload["date"])}</span></footer>
    </section>
    {briefing_sections}
  </main>
</body>
</html>"""


def _render_briefing_page(items: List[Dict], page_index: int) -> str:
    cards = "".join(
        f"""
        <article class="xhs-item quick-card">
          <div class="xhs-headline">
            <span class="xhs-rank">{rank}</span>
            <h4>{escape(item["title"])}</h4>
            <span class="xhs-score">{escape(item["source_type"])}</span>
          </div>
          <div class="quick-copy">{_markdown_to_html(item["quick_read"])}</div>
        </article>
        """
        for rank, item in enumerate(items, 1 + (page_index - 1) * 3)
    )
    return f"""
    <section class="xhs-page accent-blue">
      <div class="xhs-kicker">Page {page_index + 1} / Signals</div>
      <h1>今天值得继续跟踪的 AI 情报 0{page_index}</h1>
      <div class="xhs-list">{cards}</div>
      <footer><span>SignalForge</span><span>{page_index + 1} / 3</span></footer>
    </section>
    """


def _inline_fmt(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
    return escaped


def _markdown_to_html(markdown: str) -> str:
    parts = []
    list_open = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if not list_open:
                parts.append("<ul>")
                list_open = True
            parts.append(f"<li>{_inline_fmt(stripped[2:])}</li>")
            continue
        if list_open:
            parts.append("</ul>")
            list_open = False
        parts.append(f"<p>{_inline_fmt(stripped)}</p>")
    if list_open:
        parts.append("</ul>")
    return "".join(parts)


_SHARE_PAGE_CSS = """
body{margin:0;padding:32px;background:#f5f4f1;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
.xhs-stage{display:grid;grid-template-columns:repeat(3,360px);gap:20px}
.xhs-page{aspect-ratio:3/4;background:#fbfaf7;border:1px solid #eadfce;border-radius:18px;padding:22px;display:flex;flex-direction:column}
.xhs-kicker{font-size:12px;font-weight:700;letter-spacing:.08em;color:#9a3412}
h1{font-size:26px;line-height:1.12;margin:8px 0 14px}
.xhs-list{display:flex;flex-direction:column;gap:10px}
.xhs-item{background:white;border:1px solid #eadfce;border-radius:12px;padding:12px}
.xhs-headline{display:grid;grid-template-columns:22px 1fr auto;gap:10px;align-items:center;margin-bottom:7px}
.xhs-rank{width:22px;height:22px;border-radius:999px;background:#111827;color:white;display:grid;place-items:center;font-size:12px}
.xhs-score{font-size:11px;font-weight:700;color:#b45309}
h4{font-size:15px;line-height:1.3;margin:0}
p,li{font-size:12px;line-height:1.55;color:#374151}
.quick-copy p{margin:0 0 6px}
.quick-copy ul{margin:6px 0 6px 18px;padding:0}
footer{margin-top:auto;padding-top:14px;display:flex;justify-content:space-between;color:#6b7280;font-size:12px}
.accent-blue .xhs-kicker{color:#1d4ed8}
.accent-blue .xhs-rank{background:#1d4ed8}
.accent-blue .xhs-score{color:#2563eb}
.opp-body{display:flex;flex-direction:column;gap:6px;margin-top:4px}
.opp-row{border-top:1px solid #f0ebe2;padding-top:5px}
.opp-label{display:block;font-size:12px;font-weight:700;color:#9a3412;letter-spacing:.06em;margin-bottom:2px}
.opp-row p{margin:0;font-size:11px;line-height:1.5;color:#374151}
.opp-mvp{margin:2px 0 0 14px;padding:0;font-size:11px;color:#374151;line-height:1.5}
"""


def generate_share_page(date: str, output_path: Path) -> Path:
    payload = load_share_payload(date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_share_page_html(payload), encoding="utf-8")
    return output_path


def load_share_payload(date: str) -> Dict:
    opportunities, content_items, quick_reads = _load_share_sources(date)
    return build_share_payload(date, opportunities, content_items, quick_reads)


def _load_share_sources(date: str):
    opportunities_path = CONTENT_DIR.parent / "opportunities" / f"{date}.json"
    content_path = CONTENT_DIR / f"{date}.json"
    opportunities = []
    if opportunities_path.exists():
        opportunities = json.loads(opportunities_path.read_text(encoding="utf-8")).get("opportunities", [])
    content_items = json.loads(content_path.read_text(encoding="utf-8")) if content_path.exists() else []
    quick_reads = load_quick_reads(date)
    return opportunities, content_items, quick_reads
