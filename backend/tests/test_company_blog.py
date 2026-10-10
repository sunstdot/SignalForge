import json

import pytest

from backend.services import collector, company_blog, storage


def test_three_buckets_on_real_blog_examples():
    examples = {
        "Grab and OpenAI bring practical AI skills to Southeast Asia": "corporate",
        "New experts join Google’s AI & Economy team": "corporate",
        "Co-creating the future of fashion with Google": "corporate",
        "Making global data easier to explore": "corporate",
        "Introducing Gemini 3.8 Live": "product_launch",
        "Better prompt caching for GPT-6": "technical",
        "Open-Sourcing Rebalancer: A Generic Library": "technical",
    }
    for title, bucket in examples.items():
        assert company_blog.classify_company_blog({"source": "Google AI Blog", "title": title}) == bucket
    assert company_blog.classify_company_blog({"source_type": "anthropic_blog", "title": "Building effective agents"}) == "technical"


def test_company_duplicates_are_marked_not_deleted_without_collapsing_related_launches():
    items = [
        {"id": "a", "source": "Google DeepMind Blog", "title": "Introducing Gemini 3.8 Live", "published_date": "2026-10-10"},
        {"id": "b", "source": "Google AI Blog", "title": "Gemini 3.8 Live is now available", "published_date": "2026-10-10"},
        {"id": "c", "source": "Google AI Blog", "title": "Introducing Gemini 3.8 Audio", "published_date": "2026-10-10"},
    ]
    company_blog.dedup_company_blogs(items)
    assert items[1]["dup_of"] == "a"
    assert "dup_of" not in items[2]
    assert len(items) == 3


def test_same_title_from_different_month_is_not_a_duplicate():
    items = [
        {"id": "a", "source": "Google AI Blog", "title": "Introducing Gemini 3.8 Live", "published_date": "2026-09-01"},
        {"id": "b", "source": "Google DeepMind Blog", "title": "Gemini 3.8 Live is now available", "published_date": "2026-10-10"},
        {"id": "c", "source": "OpenAI Blog", "title": "Gemini 3.8 Live now available", "published_date": "2026-10-10"},
    ]
    company_blog.dedup_company_blogs(items)
    assert "dup_of" not in items[1]
    assert items[2]["dup_of"] == "b"


def test_policy_only_touches_company_blogs_and_is_idempotent():
    items = [
        {"id": "a", "source": "Google AI Blog", "source_type": "blog", "title": "Making global data easier to explore", "relevance_score": 8},
        {"id": "b", "source": "Google DeepMind Blog", "source_type": "blog", "title": "Introducing Gemini 3.8 Live", "relevance_score": 8},
        {"id": "c", "source": "Independent Blog", "source_type": "blog", "title": "Making global data easier to explore", "relevance_score": 8},
    ]
    company_blog.apply_company_blog_policy(items)
    company_blog.apply_company_blog_policy(items)
    assert items[0]["content_bucket"] == "corporate"
    assert items[0]["relevance_score"] == 4
    assert items[1]["content_bucket"] == "product_launch"
    assert items[1]["relevance_score"] == 10
    assert "content_bucket" not in items[2]


@pytest.mark.asyncio
async def test_collection_applies_blog_policy_before_storing(monkeypatch):
    items = [{"id": "pr", "source": "Google AI Blog", "source_type": "blog", "title": "Making global data easier to explore", "relevance_score": 8}]
    saved = []

    async def fake_fetch(*args, **kwargs):
        return items

    monkeypatch.setattr(collector, "fetch_all_sources", fake_fetch)
    monkeypatch.setattr(collector, "load_config", lambda: {"sources": {}})
    monkeypatch.setattr(collector, "store_content_items", lambda data: saved.extend(data) or len(data))
    await collector.run_collection("2026-10-10")
    assert saved[0]["content_bucket"] == "corporate"
    assert saved[0]["relevance_score"] == 4


@pytest.mark.asyncio
async def test_anthropic_article_is_not_republished_every_day(monkeypatch):
    item = {"id": "anthropic-once", "source_type": "anthropic_blog", "source": "Anthropic",
            "title": "Building effective agents", "relevance_score": 8}
    saved = []

    async def fake_fetch(*args, **kwargs):
        return [item]

    monkeypatch.setattr(collector, "fetch_all_sources", fake_fetch)
    monkeypatch.setattr(collector, "load_config", lambda: {"sources": {}})
    monkeypatch.setattr(collector, "_load_content_file", lambda day: [{"id": "anthropic-once", "source_type": "anthropic_blog"}] if day == "2026-10-09" else [])
    monkeypatch.setattr(collector, "store_content_items", lambda data: saved.extend(data) or len(data))
    assert await collector.run_collection("2026-10-10") == 0
    assert saved == []


def test_quick_reads_do_not_spend_llm_calls_on_pr_or_duplicate(monkeypatch):
    items = [
        {"id": "pr", "title": "Marketing", "content_bucket": "corporate", "original_content": "PR announcement"},
        {"id": "dup", "title": "Duplicate", "dup_of": "original", "original_content": "duplicate"},
        {"id": "tech", "title": "Engineering", "original_content": "Agent evaluation details"},
    ]
    prompts = []
    saved = []
    monkeypatch.setattr(collector, "_load_content_file", lambda date: items)
    monkeypatch.setattr(storage, "load_quick_reads", lambda date: {})
    monkeypatch.setattr(storage, "save_quick_read", lambda date, item_id, summary: saved.append(item_id))
    monkeypatch.setattr(collector, "chat", lambda messages: prompts.append(messages[0]["content"]) or json.dumps([
        {"idx": 1, "core": "detail", "points": ["point"], "insight": "useful"}
    ]))
    collector._run_batch_quick_reads("2026-10-10")
    assert saved == ["tech"]
    assert "PR announcement" not in prompts[0]
    assert "duplicate" not in prompts[0]
