"""Use Wingsbot Agent to discover Anthropic's latest technical articles."""

import hashlib
import json
import re
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlsplit, urlunsplit

ANTHROPIC_TECHNICAL_ARTICLES_PROMPT = """你是一名技术情报研究 Agent。请获取 Anthropic 官方技术博客最新的 5 篇技术文章。

执行要求：
1. 必须实际使用网页搜索和读取工具，不要依赖记忆回答。
2. 只接受 anthropic.com 官方域名下engineering和research上的文章。
4. 每个文章上有发布日期，按文章官方发布日期降序排序，只保留最新 5 篇文章。
5. 必须打开这5个候选的文章页面，核验官方英文标题、规范 URL、发布日期、所属栏目和正文内容，如果发现不符合要求，从前面排序的文章中顺位补上继续核验，直到找到符合要求的5篇文章。
6. 排除招聘、活动、纯公司公告、政策声明以及其他非技术内容。
7. 为每篇文章撰写不超过 150 个中文字符的技术摘要，并提供主题标签。
8. 如果无法核验某个字段，放弃该文章，不要猜测。

最终只输出严格 JSON，不要输出 Markdown 代码块或任何解释。结构必须是：
{
  "source": "Anthropic",
  "fetched_at": "ISO 8601",
  "articles": [
    {
      "title": "官方英文标题",
      "url": "Anthropic 官方 URL",
      "published_at": "YYYY-MM-DD",
      "section": "栏目名称",
      "summary": "中文技术摘要",
      "tags": ["anthropic", "technical", "主题"]
    }
  ]
}
"""


async def ainvoke_wingsbot(content: str, **kwargs):
    """Import lazily so an unavailable optional Agent cannot break RSS collection."""
    from .wingsbot_client import ainvoke_wingsbot as invoke

    return await invoke(content, **kwargs)


def normalize_url(url: str) -> str:
    """Return a stable URL suitable for cross-source deduplication."""
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return ""
    if not host:
        return ""
    if port:
        host = f"{host}:{port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, "", ""))


def _is_anthropic_url(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    return parts.scheme.lower() in {"http", "https"} and (
        host == "anthropic.com" or host.endswith(".anthropic.com")
    ) and parts.path.rstrip("/") != ""


def _parse_response_content(raw: str) -> Dict:
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    payload = json.loads(text)
    if not isinstance(payload, dict) or payload.get("source") != "Anthropic":
        raise ValueError("Wingsbot response has an invalid source")
    fetched_at = payload.get("fetched_at")
    if not isinstance(fetched_at, str):
        raise ValueError("Wingsbot response has an invalid fetched_at")
    try:
        datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Wingsbot response has an invalid fetched_at") from exc
    articles = payload.get("articles")
    if not isinstance(articles, list):
        raise ValueError("Wingsbot response must contain an articles array")
    required_strings = {"title", "url", "published_at", "section", "summary"}
    for article in articles:
        if not isinstance(article, dict):
            raise ValueError("Wingsbot response contains an invalid article")
        if any(not isinstance(article.get(key), str) for key in required_strings):
            raise ValueError("Wingsbot response contains an invalid article field")
        tags = article.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise ValueError("Wingsbot response contains invalid tags")
    return payload


def _article_to_item(article: Dict, target_date: str | None) -> Dict | None:
    if not isinstance(article, dict):
        return None

    title = article.get("title")
    url = article.get("url")
    published_at = article.get("published_at")
    summary = article.get("summary")
    section = article.get("section")
    tags = article.get("tags")
    if not all(isinstance(value, str) and value.strip() for value in (
        title, url, published_at, summary, section
    )):
        return None
    try:
        datetime.strptime(published_at, "%Y-%m-%d")
    except ValueError:
        return None
    if not _is_anthropic_url(url):
        return None

    canonical_url = normalize_url(url)
    if not canonical_url:
        return None
    item_id = "anthropic-" + hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:20]
    clean_tags = [tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()] if isinstance(tags, list) else []
    return {
        "id": item_id,
        "title": title.strip(),
        "url": canonical_url,
        "source": "Anthropic",
        "source_type": "anthropic_blog",
        "summary": summary.strip()[:150],
        "published_at": published_at,
        "created_at": target_date or datetime.now().strftime("%Y-%m-%d"),
        "category": [section.strip()],
        "tags": clean_tags,
        "relevance_score": 8,
    }


async def fetch_anthropic_technical_articles(target_date: str | None = None) -> List[Dict]:
    """Ask Wingsbot for verified articles; failures never block collection."""
    try:
        result = await ainvoke_wingsbot(
            ANTHROPIC_TECHNICAL_ARTICLES_PROMPT,
            session_key="signalforge:anthropic-technical-blog",
            structured=True,
        )
        if not getattr(result, "ok", False):
            raise RuntimeError(getattr(result, "error", "Wingsbot invocation failed"))
        payload = _parse_response_content(str(getattr(result, "content", "")))

        items = []
        seen_urls = set()
        for article in payload["articles"]:
            item = _article_to_item(article, target_date)
            if item is None or item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            items.append(item)
        items.sort(key=lambda item: item["published_at"], reverse=True)
        return items[:5]
    except Exception as exc:
        print(f"  ✗ Anthropic Blog failed: {exc}")
        return []
