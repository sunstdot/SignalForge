"""手动情报录入 API"""
import asyncio
import json
import re
import time
from html import escape
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_SHARE_PAGES_DIR = Path(__file__).parent.parent / "docs" / "share-pages"

from services.storage import (
    get_manual_intel_items,
    get_manual_intel_item_by_id,
    create_manual_intel_item,
    update_manual_intel_item,
    delete_manual_intel_item,
)
from services.llm_client import chat_async

router = APIRouter()

_background_tasks: set = set()


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


class CreateManualIntelRequest(BaseModel):
    url: str
    source_platform: str = "other"
    user_note: str = ""


_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _is_weixin_url(url: str) -> bool:
    return "mp.weixin.qq.com" in url


def _is_x_url(url: str) -> bool:
    return "x.com/" in url or "twitter.com/" in url


async def _expand_tco_url(short_url: str) -> str:
    """Follow t.co redirect and return the final URL."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.head(short_url)
            return str(resp.url)
    except Exception:
        return short_url


async def _fetch_x_content(url: str) -> tuple[str, str]:
    """Fetch X/Twitter post via oEmbed API (free, no auth required).
    If the tweet body is only a t.co link, expands it and fetches the linked article."""
    import httpx
    from bs4 import BeautifulSoup
    oembed_url = f"https://publish.twitter.com/oembed?url={url}&omit_script=true"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(oembed_url)
        if resp.status_code != 200:
            return "", ""
        data = resp.json()
        author = data.get("author_name", "")
        html = data.get("html", "")
        soup = BeautifulSoup(html, "html.parser")

        # Collect t.co links before stripping them
        tco_links = [a["href"] for a in soup.find_all("a", href=True) if "t.co/" in a.get("href", "")]

        for a in soup.find_all("a"):
            a.decompose()
        tweet_text = soup.get_text(separator=" ", strip=True)

        # If the tweet has meaningful text, use it directly
        if len(tweet_text) > 20:
            title = f"{author} 的推文" if author else "X 推文"
            return title, tweet_text[:6000]

        # Tweet is just a link — expand t.co and fetch the real article
        if tco_links:
            expanded = await _expand_tco_url(tco_links[0])
            print(f"[manual-intel] X tweet is link-only, fetching expanded URL: {expanded}")
            # x.com/i/article/ are X long-form articles — JS-rendered, cannot fetch
            if expanded and not _is_x_url(expanded):
                art_title, art_snippet = await _fetch_url_content(expanded)
                if art_snippet:
                    prefix = f"（来自 {author} 的推文分享）\n\n" if author else ""
                    return art_title or f"{author} 分享的文章", prefix + art_snippet

        return (f"{author} 的推文" if author else "X 推文"), tweet_text


async def _fetch_url_content(url: str) -> tuple[str, str]:
    """Fetch a URL and return (title, content_snippet). Never raises — returns empty strings on failure."""
    try:
        import httpx
        from bs4 import BeautifulSoup

        if _is_x_url(url):
            return await _fetch_x_content(url)

        headers = {"User-Agent": _BROWSER_UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return "", ""
            soup = BeautifulSoup(resp.text, "html.parser")

            if _is_weixin_url(url):
                # WeChat article: dedicated title and content nodes
                title_tag = (
                    soup.find(id="activity-name")
                    or soup.find(class_="rich_media_title")
                    or soup.title
                )
                title = title_tag.get_text(strip=True) if title_tag else ""
                content_tag = soup.find(id="js_content") or soup.find(class_="rich_media_content")
                if content_tag:
                    for tag in content_tag(["script", "style"]):
                        tag.decompose()
                    snippet = content_tag.get_text(separator=" ", strip=True)[:6000]
                else:
                    snippet = ""
                return title, snippet

            title = soup.title.get_text(strip=True) if soup.title else ""
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            snippet = soup.get_text(separator=" ", strip=True)[:6000]
            return title, snippet
    except Exception as e:
        print(f"[manual-intel] fetch failed for {url}: {e}")
        return "", ""


async def _run_quick_read(item_id: str):
    """Auto-run quick_read analysis and persist result."""
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        return

    title = item.get("title", "")
    snippet = item.get("content_snippet", "")
    user_note = item.get("user_note", "")

    # When content can't be fetched (JS-heavy pages), fall back to user note
    meaningful_snippet = snippet.strip() if len(snippet.strip()) > 50 else ""
    if not meaningful_snippet and not user_note.strip():
        return
    content_source = meaningful_snippet or f"（原文无法自动获取，以下为用户笔记）\n{user_note.strip()}"

    prompt = f"""请对以下文章进行速读总结，帮助读者快速了解核心内容。

文章标题：{title}
原文内容（节选）：
{content_source}

请用中文输出，严格使用以下 Markdown 格式：
**核心内容**：用 2-3 句话说清楚文章讲了什么（面向技术/创业读者）

**关键信息**：
- 要点一
- 要点二
- 要点三（共 3-5 条，每条以 - 开头）

**值得关注**：这篇文章最有价值的一个洞察或信息（1 句话）

直接输出内容，不要重复标题。"""

    try:
        quick_read = (await chat_async([{"role": "user", "content": prompt}])).strip()
        update_manual_intel_item(item_id, {"quick_read": quick_read})
    except Exception as e:
        print(f"[manual-intel] quick_read failed for {item_id}: {e}")
        return

    try:
        import services.wiki_builder as _wiki
        await _wiki.process_article(item_id)
    except Exception as e:
        print(f"[manual-intel] wiki pipeline failed for {item_id}: {e}")


async def _generate_business_opps(item: dict) -> list:
    """Run business opportunity analysis for an item. Returns list (empty on failure)."""
    title = item.get("title", "")
    snippet = item.get("content_snippet", "")

    prompt = f"""你是一位经验丰富的 AI 产品经理和连续创业者，擅长从技术内容中发现真实可落地的商业机会。

# 开发者背景
- 独立开发者，无团队
- 技术栈：Python / Next.js
- 可接受面向全球或中文市场的产品

# 文章信息
标题：{title}
内容节选：{snippet[:3000]}

# 任务
基于以上文章，识别 1-3 个可落地的商业机会。如果文章内容无商业机会（纯商业新闻、人事变动等），返回空数组 []。

# 输出格式（严格 JSON，不要 markdown 代码块）
[
  {{
    "opportunity_title": "产品方向名称（30字以内）",
    "core_insight": "这个技术能力如何支撑此产品，之前为何不可行（60字以内）",
    "product_form": "帮助[目标用户]解决[具体问题]的[产品类型]",
    "target_users": "用户画像：职业/场景/痛点/付费意愿（40字以内）",
    "mvp_features": ["核心功能1", "核心功能2", "核心功能3"],
    "business_model": "盈利方式及定价（30字以内）",
    "risks": "最大风险（40字以内）",
    "scores": {{
      "pain_point": 4,
      "market_size": 3,
      "tech_timing": 5,
      "buildability": 4
    }},
    "total_score": 16
  }}
]"""

    try:
        raw = (await chat_async([{"role": "user", "content": prompt}], provider="deepseek")).strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        result = json.loads(match.group(0) if match else raw)
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"[manual-intel] business_opps failed for {item.get('id')}: {e}")
        return []


async def _generate_rdev_opps(item: dict) -> list:
    """Run R&D opportunity analysis for an item. Returns list (empty on failure)."""
    title = item.get("title", "")
    snippet = item.get("content_snippet", "")

    prompt = f"""你是一位深度嵌入顶级互联网大厂的 AI 架构师兼技术顾问，深知研发团队的真实痛点。

# 文章信息
标题：{title}
内容节选：{snippet[:3000]}

# 任务
基于以上文章，挖掘 1-3 个可落地的研发提效或业务赋能机会。如文章无技术内容，返回空数组 []。

# 输出格式（严格 JSON，不要 markdown 代码块）
[
  {{
    "type": "研发提效",
    "title": "一句话方案名称（20字以内）",
    "trigger": "哪个技术点触发了这个机会（30字以内）",
    "scenario": "在[具体场景]中，目前做法是[现有做法]，核心痛点在于[问题所在]（80字以内）",
    "ai_solution": "新技术如何重构这个场景（80字以内）",
    "implementation": "具体集成形态，如VS Code插件/GitLab Webhook等（60字以内）",
    "audience": ["大前端", "客户端"],
    "impact": "量化预期收益（50字以内）",
    "difficulty": "低",
    "scores": {{
      "efficiency": 8,
      "feasibility": 7,
      "business_impact": 6,
      "overall": 8
    }},
    "total_score": 8
  }}
]

type 只能是"研发提效"或"业务赋能"。difficulty 只能是"低"、"中"、"高"。"""

    try:
        raw = (await chat_async([{"role": "user", "content": prompt}], provider="deepseek")).strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        result = json.loads(match.group(0) if match else raw)
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"[manual-intel] rdev_opps failed for {item.get('id')}: {e}")
        return []


@router.get("")
async def list_items(source_platform: Optional[str] = None):
    items = get_manual_intel_items(source_platform=source_platform)
    return {"items": items}


@router.get("/{item_id}")
async def get_item(item_id: str):
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


class GenerateSharePageRequest(BaseModel):
    item_ids: List[str]


@router.post("/generate-share-page")
async def generate_share_page(req: GenerateSharePageRequest):
    all_items = [get_manual_intel_item_by_id(iid) for iid in req.item_ids]
    items = [i for i in all_items if i is not None and i.get("quick_read")]
    if not items:
        raise HTTPException(status_code=400, detail="No items with quick read found")

    slug = f"manual-intel-{int(time.time())}"
    html = _render_manual_intel_html(items, slug)

    _SHARE_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    (_SHARE_PAGES_DIR / f"{slug}.html").write_text(html, encoding="utf-8")

    return {"url": f"/api/share-pages/{slug}.html"}


@router.post("", status_code=201)
async def create_item(body: CreateManualIntelRequest):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    if not _is_safe_url(url):
        raise HTTPException(status_code=400, detail="url must be a valid http or https URL")

    title, content_snippet = await _fetch_url_content(url)
    if not title:
        title = url

    item = create_manual_intel_item({
        "url": url,
        "title": title,
        "source_platform": body.source_platform,
        "user_note": body.user_note,
        "content_snippet": content_snippet,
    })

    task = asyncio.create_task(_run_quick_read(item["id"]))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return item


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    ok = delete_manual_intel_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.post("/{item_id}/reanalyze")
async def reanalyze_item(item_id: str):
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    update_manual_intel_item(item_id, {"quick_read": ""})
    task = asyncio.create_task(_run_quick_read(item_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"ok": True, "message": "Quick read re-analysis started"}


@router.post("/{item_id}/generate-business")
async def generate_business(item_id: str):
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    business_opps = await _generate_business_opps(item)
    update_manual_intel_item(item_id, {"business_opps": business_opps})
    return {"business_opps": business_opps}


@router.post("/{item_id}/generate-rdev")
async def generate_rdev(item_id: str):
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    rdev_opps = await _generate_rdev_opps(item)
    update_manual_intel_item(item_id, {"rdev_opps": rdev_opps})
    return {"rdev_opps": rdev_opps}


_PLATFORM_LABELS = {
    "X": "𝕏", "Reddit": "Reddit", "Blog": "Blog",
    "HackerNews": "HN", "other": "其他",
}

_MANUAL_INTEL_CSS = """
body{margin:0;padding:32px;background:#f5f4f1;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
.xhs-stage{display:grid;grid-template-columns:repeat(3,360px);gap:20px}
.xhs-page{aspect-ratio:3/4;background:#fbfaf7;border:1px solid #eadfce;border-radius:18px;padding:22px;display:flex;flex-direction:column;overflow:hidden}
.xhs-kicker{font-size:12px;font-weight:700;letter-spacing:.08em;color:#9a3412}
h1{font-size:22px;line-height:1.12;margin:8px 0 12px}
.xhs-list{display:flex;flex-direction:column;gap:10px;overflow:hidden}
.xhs-item{background:white;border:1px solid #eadfce;border-radius:12px;padding:12px;overflow:hidden}
.xhs-headline{display:grid;grid-template-columns:22px 1fr;gap:8px;align-items:flex-start;margin-bottom:6px}
.xhs-rank{width:22px;height:22px;border-radius:999px;background:#111827;color:white;display:grid;place-items:center;font-size:12px;flex-shrink:0}
h4{font-size:13px;line-height:1.35;margin:0;color:#111827;font-weight:700}
p,li{font-size:11px;line-height:1.55;color:#374151}
.quick-copy p{margin:0 0 4px}
.quick-copy ul{margin:4px 0 4px 14px;padding:0}
.note{font-style:italic;color:#6b7280;font-size:11px;margin:0 0 4px}
footer{margin-top:auto;padding-top:12px;display:flex;justify-content:space-between;color:#6b7280;font-size:11px}
"""


def _md_to_html(text: str) -> str:
    parts = []
    list_open = False
    for line in text.splitlines():
        s = line.strip()
        if not s:
            if list_open:
                parts.append("</ul>")
                list_open = False
            continue
        if s.startswith("- ") or s.startswith("• "):
            if not list_open:
                parts.append("<ul>")
                list_open = True
            content = s[2:].strip()
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escape(content))
            parts.append(f"<li>{content}</li>")
        else:
            if list_open:
                parts.append("</ul>")
                list_open = False
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escape(s))
            parts.append(f"<p>{content}</p>")
    if list_open:
        parts.append("</ul>")
    return "".join(parts)


def _render_manual_intel_html(items: list, slug: str) -> str:
    date_str = items[0].get("added_at", "")[:10] if items else ""

    ITEMS_PER_PAGE = 3
    pages = [items[i:i + ITEMS_PER_PAGE] for i in range(0, len(items), ITEMS_PER_PAGE)]

    page_htmls = []
    for page_idx, page_items in enumerate(pages):
        item_cards = []
        for rank, item in enumerate(page_items, 1):
            title = escape(item.get("title") or item.get("url", ""))
            note = item.get("user_note", "")
            note_html = f'<p class="note">💬 {escape(note)}</p>' if note else ""
            quick_html = _md_to_html(item.get("quick_read", ""))
            item_cards.append(f"""
        <article class="xhs-item">
          <div class="xhs-headline">
            <span class="xhs-rank">{rank}</span>
            <h4>{title}</h4>
          </div>
          {note_html}
          <div class="quick-copy">{quick_html}</div>
        </article>""")

        page_no = page_idx + 1
        total = len(pages)
        page_htmls.append(f"""
    <section class="xhs-page">
      <div class="xhs-kicker">📌 我的情报精选 · {page_no}/{total}</div>
      <h1>精选情报速读</h1>
      <div class="xhs-list">{"".join(item_cards)}</div>
      <footer><span>SignalForge 手动情报</span><span>{escape(date_str)}</span></footer>
    </section>""")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>我的情报收藏精选</title>
  <style>{_MANUAL_INTEL_CSS}</style>
</head>
<body>
  <main class="xhs-stage">
    {"".join(page_htmls)}
  </main>
</body>
</html>"""
