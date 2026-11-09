"""可插拔的搜索后端。

调研系统只依赖 SearchBackend 协议，不依赖具体厂商。换取搜索源时只改
`resolve_backend()` 的选择逻辑，流水线代码不变。

为什么需要这层抽象：外部搜索服务的可用性和额度都会变（实测 Brave 从本机连不上、
DuckDuckGo 返回反爬页、公共 SearXNG 实例不可达），把厂商写进流水线会让整个系统
跟着某个服务的状态一起坏掉。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Sequence

import httpx

# 来源分层。调研结论的可信度依赖这个分层，而不是来源数量。
# official  : 公司官网、招聘页、公告、监管文件
# firsthand: 当事人自述——播客/访谈/演讲/LinkedIn/个人博客
# media    : 有编辑流程的媒体（Bloomberg / WIRED / The Verge / BI）
# secondary: 转述与二手编译（公众号转载、聚合站）
SOURCE_TIERS = ("official", "firsthand", "media", "secondary")


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str = ""
    published: Optional[str] = None
    source_tier: str = "secondary"
    # 搜索服务已经返回正文时直接带上，省一次抓取；否则为 None。
    raw_content: Optional[str] = None
    engine: str = ""
    score: Optional[float] = None

    def as_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "published": self.published,
            "source_tier": self.source_tier,
            "raw_content": self.raw_content,
            "engine": self.engine,
            "score": self.score,
        }


class SearchBackend(Protocol):
    name: str

    def available(self) -> bool:
        """是否具备调用条件（通常是 key 是否存在）。"""

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        domains: Optional[Sequence[str]] = None,
    ) -> List[SearchResult]:
        ...  # pragma: no cover


# ───────────────────────── 站点分层 ─────────────────────────

OFFICIAL_DOMAINS = (
    "anthropic.com", "openai.com", "deepmind.google", "ai.meta.com",
    "careers.", "jobs.", "greenhouse.io",
)
FIRSTHAND_DOMAINS = (
    "dwarkesh.com", "lenny", "substack.com", "youtube.com", "youtu.be",
    "linkedin.com", "podcasts.", "buzzsprout.com", "spotify.com",
)
MEDIA_DOMAINS = (
    "bloomberg.com", "wired.com", "theverge.com", "theinformation.com",
    "businessinsider.com", "fortune.com", "techcrunch.com", "reuters.com",
    "ft.com", "wsj.com", "nytimes.com", "apnews.com", "forbes.com",
)


def classify_domain(url: str) -> str:
    """按域名给来源分层。域名不在任何名单里时按 secondary 处理——宁可按低估。"""
    host = (url or "").lower()
    for marker in OFFICIAL_DOMAINS:
        if marker in host:
            return "official"
    for marker in FIRSTHAND_DOMAINS:
        if marker in host:
            return "firsthand"
    for marker in MEDIA_DOMAINS:
        if marker in host:
            return "media"
    return "secondary"


# ───────────────────────── Tavily ─────────────────────────

class TavilyBackend:
    """Tavily 搜索。面向 LLM 场景，可直接返回清洗后的正文。"""

    name = "tavily"
    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None, *, timeout: float = 30.0):
        self.api_key = (api_key if api_key is not None else os.getenv("TAVILY_API_KEY", "")).strip()
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        domains: Optional[Sequence[str]] = None,
        include_raw: bool = True,
    ) -> List[SearchResult]:
        if not self.available():
            raise RuntimeError("TAVILY_API_KEY 未配置")
        payload = {
            "query": query,
            "max_results": max(1, min(top_k, 20)),
            "search_depth": "advanced",
            "include_raw_content": include_raw,
        }
        if domains:
            payload["include_domains"] = list(domains)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self.ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            SearchResult(
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=item.get("content", "") or "",
                published=item.get("published_date"),
                source_tier=classify_domain(item.get("url", "")),
                raw_content=item.get("raw_content"),
                engine=self.name,
                score=item.get("score"),
            )
            for item in data.get("results", [])
            if item.get("url")
        ]


# ───────────────────────── Hacker News Algolia ─────────────────────────

class HackerNewsBackend:
    """无 key 的兜底搜索。只覆盖技术讨论，不能替代通用搜索。"""

    name = "hn"
    ENDPOINT = "https://hn.algolia.com/api/v1/search"

    def __init__(self, *, timeout: float = 20.0):
        self.timeout = timeout

    def available(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        domains: Optional[Sequence[str]] = None,
    ) -> List[SearchResult]:
        params = {"query": query, "hitsPerPage": max(1, min(top_k, 30)), "tags": "story"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self.ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
        results = []
        for hit in data.get("hits", []):
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            results.append(
                SearchResult(
                    url=url,
                    title=hit.get("title") or "",
                    snippet=hit.get("story_text") or "",
                    published=hit.get("created_at"),
                    source_tier=classify_domain(url),
                    engine=self.name,
                    score=hit.get("points"),
                )
            )
        return results


def resolve_backend(name: Optional[str] = None) -> SearchBackend:
    """按配置挑一个后端。

    默认顺序：显式指定 → TAVILY_API_KEY 存在时用 tavily → 退回 hn。
    hn 只覆盖技术讨论，退回它是为了在没有 key 时不至于直接报错，
    调用方应通过 `degraded` 标记让用户知道覆盖不完整。
    """
    key = (name or os.getenv("RESEARCH_SEARCH_BACKEND", "")).strip().lower()
    if key == "hn":
        return HackerNewsBackend()
    if key == "tavily":
        return TavilyBackend()
    tavily = TavilyBackend()
    if tavily.available():
        return tavily
    return HackerNewsBackend()


def backend_status() -> Dict[str, object]:
    """给前端和健康检查用：当前用的是谁、是不是降级状态。"""
    backend = resolve_backend()
    return {
        "backend": backend.name,
        "degraded": backend.name != "tavily",
        "tavily_configured": TavilyBackend().available(),
    }
