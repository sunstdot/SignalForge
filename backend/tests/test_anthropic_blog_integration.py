import pytest

from backend.services import briefing_generator, collector


@pytest.mark.asyncio
async def test_collector_appends_agent_articles_without_replacing_rss(monkeypatch):
    rss_item = {
        "id": "rss-1",
        "title": "RSS copy",
        "url": "https://www.anthropic.com/research/shared",
        "source": "Anthropic RSS",
        "source_type": "rss",
        "relevance_score": 7,
    }
    new_agent_item = {
        "id": "agent-new",
        "title": "Agent only",
        "url": "https://www.anthropic.com/engineering/new",
        "source": "Anthropic",
        "source_type": "anthropic_blog",
        "relevance_score": 8,
    }
    duplicate_agent_item = {
        **new_agent_item,
        "id": "agent-duplicate",
        "title": "Agent duplicate",
        "url": "https://www.anthropic.com/research/shared/?utm_source=agent",
    }

    async def fake_rss(*args, **kwargs):
        return [rss_item]

    async def fake_anthropic(*args, **kwargs):
        return [duplicate_agent_item, new_agent_item]

    monkeypatch.setattr(collector, "fetch_rss_feeds", fake_rss)
    monkeypatch.setattr(collector, "fetch_anthropic_technical_articles", fake_anthropic)

    result = await collector.fetch_all_sources(
        {"sources": {"rss": {"enabled": True}}}, target_date="2026-09-17"
    )

    assert [item["id"] for item in result] == ["rss-1", "agent-new"]


@pytest.mark.asyncio
async def test_collector_preserves_existing_item_with_malformed_url(monkeypatch):
    malformed_item = {
        "id": "rss-malformed",
        "title": "Existing item",
        "url": "https://example.com:invalid/article",
        "source": "Existing RSS",
        "source_type": "rss",
        "relevance_score": 7,
    }

    async def fake_rss(*args, **kwargs):
        return [malformed_item]

    async def fake_anthropic(*args, **kwargs):
        return []

    monkeypatch.setattr(collector, "fetch_rss_feeds", fake_rss)
    monkeypatch.setattr(collector, "fetch_anthropic_technical_articles", fake_anthropic)

    result = await collector.fetch_all_sources({"sources": {"rss": {"enabled": True}}})

    assert result == [malformed_item]


def test_briefing_always_places_anthropic_agent_articles_last(monkeypatch):
    items = [
        {
            "id": "agent",
            "title": "Anthropic article",
            "source": "Anthropic",
            "source_type": "anthropic_blog",
            "url": "https://anthropic.com/research/new",
            "summary": "summary",
            "category": ["Research"],
            "relevance_score": 100,
            "published_at": "2026-09-17",
            "created_at": "2026-09-17",
        },
        {
            "id": "rss",
            "title": "RSS article",
            "source": "Existing RSS",
            "source_type": "rss",
            "url": "https://example.com/rss",
            "summary": "summary",
            "category": [],
            "relevance_score": 1,
            "created_at": "2026-09-17",
        },
    ]
    monkeypatch.setattr(briefing_generator, "_load_content_file", lambda date: items)
    monkeypatch.setattr(briefing_generator, "get_all_dates", lambda: ["2026-09-17"])
    monkeypatch.setattr(briefing_generator, "save_briefing_file", lambda briefing: None)

    briefing = briefing_generator.generate_briefing_for_date("2026-09-17")

    assert [item["id"] for item in briefing["items"]] == ["rss", "agent"]


def test_briefing_keeps_five_newest_anthropic_articles(monkeypatch):
    items = []
    for day in range(12, 18):
        items.append(
            {
                "id": f"agent-{day}",
                "title": f"Anthropic article {day}",
                "source": "Anthropic",
                "source_type": "anthropic_blog",
                "url": f"https://anthropic.com/research/{day}",
                "summary": "summary",
                "category": ["Research"],
                "relevance_score": 8,
                "published_at": f"2026-09-{day:02d}",
                "created_at": "2026-09-17",
            }
        )
    monkeypatch.setattr(briefing_generator, "_load_content_file", lambda date: items)
    monkeypatch.setattr(briefing_generator, "get_all_dates", lambda: ["2026-09-17"])
    monkeypatch.setattr(briefing_generator, "save_briefing_file", lambda briefing: None)

    briefing = briefing_generator.generate_briefing_for_date("2026-09-17")

    assert [item["id"] for item in briefing["items"]] == [
        "agent-17",
        "agent-16",
        "agent-15",
        "agent-14",
        "agent-13",
    ]
