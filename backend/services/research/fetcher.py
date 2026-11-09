"""正文抓取。

调研引用的一手材料大量是访谈、播客页、招聘 JD 和媒体报道，反爬形态各不相同。
这里只做三件事：取回 HTML、抽出正文、判断失败原因。

判断失败原因比抽取正文更重要：付费墙和反爬如果被当成"页面没有这条信息"，
最后写出来的报告会在关键结论上悄悄变薄，而且看不出缺了什么。
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from .models import FETCH_STATUSES

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 常见付费墙/反爬标记。命中即判定抓不到正文，而不是把提示页当正文。
PAYWALL_MARKERS = (
    "subscribe to continue", "subscribers only", "already a subscriber",
    "this article is for subscribers", "sign in to read",
    "订阅后阅读", "付费阅读", "开通会员",
)
BLOCK_MARKERS = (
    "access denied", "are you a robot", "unusual traffic",
    "enable javascript and cookies", "cf-browser-verification",
    "请完成安全验证", "访问异常",
)

MIN_USEFUL_CHARS = 400


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "footer", "header", "form"]):
        tag.decompose()
    # 优先用语义容器，退化到 body
    container = soup.find("article") or soup.find("main") or soup.body or soup
    text = container.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _classify(html: str, text: str, status_code: int) -> Tuple[str, str]:
    lowered = (html or "")[:20000].lower()
    for marker in BLOCK_MARKERS:
        if marker in lowered:
            return "blocked", f"命中反爬标记：{marker}"
    for marker in PAYWALL_MARKERS:
        if marker in lowered:
            return "paywalled", f"命中付费墙标记：{marker}"
    if status_code in (401, 403):
        return "blocked", f"HTTP {status_code}"
    if status_code == 402:
        return "paywalled", f"HTTP {status_code}"
    if len(text) < MIN_USEFUL_CHARS:
        return "ok", f"正文较短（{len(text)} 字符），可能抽取不完整"
    return "ok", ""


async def fetch_document(url: str, *, timeout: float = 25.0, max_chars: int = 200_000) -> dict:
    """取回一个 URL 的正文。

    返回 dict：status / text / detail / http_status
    status 取值见 models.FETCH_STATUSES，调用方必须据此决定这个来源能不能参与核验。
    """
    if not url or not url.startswith(("http://", "https://")):
        return {"status": "skipped", "text": "", "detail": "非 http(s) URL", "http_status": None}

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=headers
        ) as client:
            resp = await client.get(url)
    except httpx.TimeoutException:
        return {"status": "unreachable", "text": "", "detail": "超时", "http_status": None}
    except httpx.HTTPError as exc:
        return {"status": "unreachable", "text": "", "detail": f"{type(exc).__name__}: {exc}", "http_status": None}

    content_type = resp.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        return {
            "status": "skipped",
            "text": "",
            "detail": f"非文本内容：{content_type}",
            "http_status": resp.status_code,
        }

    html = resp.text
    text = _clean_text(html)[:max_chars]
    status, detail = _classify(html, text, resp.status_code)

    if resp.status_code >= 400 and status == "ok":
        status, detail = "error", f"HTTP {resp.status_code}"

    return {
        "status": status if status in FETCH_STATUSES else "error",
        "text": text,
        "detail": detail,
        "http_status": resp.status_code,
    }
