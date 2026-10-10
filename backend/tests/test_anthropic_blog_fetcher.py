import json
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_fetcher_returns_verified_articles_newest_first(monkeypatch):
    from backend.services import anthropic_blog_fetcher as fetcher

    captured = {}
    payload = {
        "source": "Anthropic",
        "fetched_at": "2026-09-17T08:00:00Z",
        "articles": [
            {
                "title": "Older technical article",
                "url": "https://www.anthropic.com/research/older",
                "published_at": "2026-09-15",
                "section": "Research",
                "summary": "较早文章摘要",
                "tags": ["anthropic", "technical", "research"],
            },
            {
                "title": "Newest technical article",
                "url": "https://www.anthropic.com/engineering/newest",
                "published_at": "2026-09-17",
                "section": "Engineering",
                "summary": "最新文章摘要",
                "tags": ["anthropic", "technical", "engineering"],
            },
        ],
    }

    async def fake_invoke(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            ok=True,
            content=f"```json\n{json.dumps(payload)}\n```",
            error=None,
        )

    monkeypatch.setattr(fetcher, "ainvoke_wingsbot", fake_invoke)

    items = await fetcher.fetch_anthropic_technical_articles("2026-09-17")

    assert [item["title"] for item in items] == [
        "Newest technical article",
        "Older technical article",
    ]
    assert items[0] == {
        "id": items[0]["id"],
        "title": "Newest technical article",
        "url": "https://www.anthropic.com/engineering/newest",
        "source": "Anthropic",
        "source_type": "anthropic_blog",
        "summary": "最新文章摘要",
        "published_at": "2026-09-17",
        "created_at": "2026-09-17",
        "category": ["Engineering"],
        "tags": ["anthropic", "technical", "engineering"],
        "relevance_score": 8,
    }
    assert "实际使用网页搜索和读取工具" in captured["prompt"]
    assert "只输出严格 JSON" in captured["prompt"]
    assert captured["kwargs"] == {
        "session_key": "signalforge:anthropic-technical-blog",
        "structured": True,
    }


@pytest.mark.asyncio
async def test_fetcher_filters_invalid_external_and_duplicate_articles(monkeypatch):
    from backend.services import anthropic_blog_fetcher as fetcher

    valid = {
        "title": "Valid",
        "url": "https://anthropic.com/research/valid",
        "published_at": "2026-09-17",
        "section": "Research",
        "summary": "摘要",
        "tags": ["anthropic"],
    }
    payload = {
        "source": "Anthropic",
        "fetched_at": "2026-09-17T08:00:00Z",
        "articles": [
            valid,
            {**valid, "url": "https://anthropic.com/research/valid/?utm_source=test"},
            {**valid, "url": "https://example.com/research/external"},
            {**valid, "url": "https://evil-anthropic.com/research/lookalike"},
            {**valid, "url": "https://anthropic.com:invalid/research/bad-port"},
            {**valid, "url": "https://anthropic.com/research/missing-date", "published_at": ""},
            {**valid, "url": "https://anthropic.com/research/bad-date", "published_at": "17-09-2026"},
        ]
    }

    async def fake_invoke(*args, **kwargs):
        return SimpleNamespace(ok=True, content=json.dumps(payload), error=None)

    monkeypatch.setattr(fetcher, "ainvoke_wingsbot", fake_invoke)

    items = await fetcher.fetch_anthropic_technical_articles()

    assert [item["url"] for item in items] == ["https://anthropic.com/research/valid"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(ok=True, content="not json", error=None),
        SimpleNamespace(ok=False, content="", error="failed"),
    ],
)
async def test_fetcher_skips_malformed_or_failed_agent_response(monkeypatch, response):
    from backend.services import anthropic_blog_fetcher as fetcher

    async def fake_invoke(*args, **kwargs):
        return response

    monkeypatch.setattr(fetcher, "ainvoke_wingsbot", fake_invoke)

    assert await fetcher.fetch_anthropic_technical_articles() == []


@pytest.mark.asyncio
async def test_fetcher_accepts_structured_result(monkeypatch):
    from backend.services import anthropic_blog_fetcher as fetcher

    payload = {
        "source": "Anthropic",
        "fetched_at": "2026-09-17T17:29:00+08:00",
        "articles": [],
    }
    async def fake_invoke(*args, **kwargs):
        return SimpleNamespace(ok=True, content=json.dumps(payload), error=None)

    monkeypatch.setattr(fetcher, "ainvoke_wingsbot", fake_invoke)

    assert await fetcher.fetch_anthropic_technical_articles() == []


@pytest.mark.asyncio
async def test_fetcher_skips_agent_exception(monkeypatch):
    from backend.services import anthropic_blog_fetcher as fetcher

    async def fake_invoke(*args, **kwargs):
        raise RuntimeError("agent unavailable")

    monkeypatch.setattr(fetcher, "ainvoke_wingsbot", fake_invoke)

    assert await fetcher.fetch_anthropic_technical_articles() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"source": "Other", "fetched_at": "2026-09-17T08:00:00Z", "articles": []},
        {"source": "Anthropic", "fetched_at": "not-a-date", "articles": []},
        {
            "source": "Anthropic",
            "fetched_at": "2026-09-17T08:00:00Z",
            "articles": [
                {
                    "title": "Article",
                    "url": "https://anthropic.com/research/article",
                    "published_at": "2026-09-17",
                    "section": "Research",
                    "summary": "摘要",
                    "tags": "anthropic",
                }
            ],
        },
    ],
)
async def test_fetcher_rejects_response_that_does_not_match_schema(monkeypatch, payload):
    from backend.services import anthropic_blog_fetcher as fetcher

    async def fake_invoke(*args, **kwargs):
        return SimpleNamespace(ok=True, content=json.dumps(payload), error=None)

    monkeypatch.setattr(fetcher, "ainvoke_wingsbot", fake_invoke)

    assert await fetcher.fetch_anthropic_technical_articles() == []
