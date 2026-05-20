import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def isolated_wiki(monkeypatch, tmp_path):
    import services.storage as s
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr(s, "WIKI_DIR", wiki_dir)
    yield wiki_dir


@pytest.fixture
def vault_path(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


# ── _slugify ────────────────────────────────────────────────────────────────

def test_slugify_basic():
    from services.wiki_builder import _slugify
    assert _slugify("In-Context Learning") == "in-context-learning"


def test_slugify_special_chars():
    from services.wiki_builder import _slugify
    assert _slugify("RAG: Retrieval & Search!") == "rag-retrieval-search"


def test_slugify_long_string():
    from services.wiki_builder import _slugify
    result = _slugify("a" * 100)
    assert len(result) <= 60


# ── _extract_concepts ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_concepts_returns_list():
    from services.wiki_builder import _extract_concepts

    mock_response = '[{"name": "RAG", "description": "Retrieval Augmented Generation"}]'
    with patch("services.wiki_builder.chat_async", new=AsyncMock(return_value=mock_response)):
        result = await _extract_concepts("Test Title", "Some content")
    assert isinstance(result, list)
    assert result[0]["name"] == "RAG"


@pytest.mark.asyncio
async def test_extract_concepts_handles_llm_failure():
    from services.wiki_builder import _extract_concepts

    with patch("services.wiki_builder.chat_async", new=AsyncMock(side_effect=Exception("LLM error"))):
        result = await _extract_concepts("Title", "Content")
    assert result == []


@pytest.mark.asyncio
async def test_extract_concepts_handles_bad_json():
    from services.wiki_builder import _extract_concepts

    with patch("services.wiki_builder.chat_async", new=AsyncMock(return_value="not json at all")):
        result = await _extract_concepts("Title", "Content")
    assert result == []


# ── _find_candidate_articles ─────────────────────────────────────────────────

def test_find_candidates_by_shared_concept(monkeypatch):
    from services.wiki_builder import _find_candidate_articles
    import services.storage as s

    s.upsert_wiki_article_node("item-A", "article-a", ["RAG", "LLM"], [])
    s.upsert_wiki_article_node("item-B", "article-b", ["Vector Search"], [])

    fake_item_a = {"id": "item-A", "title": "Article A", "content_snippet": "content A"}
    monkeypatch.setattr(s, "get_manual_intel_item_by_id",
                        lambda iid: fake_item_a if iid == "item-A" else None)

    new_concepts = [{"name": "RAG", "description": "def"}]
    candidates = _find_candidate_articles(new_concepts, "item-NEW")
    assert len(candidates) == 1
    assert candidates[0]["id"] == "item-A"


def test_find_candidates_excludes_self(monkeypatch):
    from services.wiki_builder import _find_candidate_articles
    import services.storage as s

    s.upsert_wiki_article_node("item-A", "article-a", ["RAG"], [])

    new_concepts = [{"name": "RAG", "description": "def"}]
    candidates = _find_candidate_articles(new_concepts, "item-A")
    assert candidates == []


# ── _analyze_connections ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_connections_no_candidates():
    from services.wiki_builder import _analyze_connections
    result = await _analyze_connections({"title": "T", "content_snippet": "c"}, [])
    assert result == {"related_articles": [], "additional_insights": ""}


@pytest.mark.asyncio
async def test_analyze_connections_returns_related():
    from services.wiki_builder import _analyze_connections

    mock_response = '{"related_articles": [{"title": "Other Article", "reason": "Both cover RAG"}], "additional_insights": ""}'
    with patch("services.wiki_builder.chat_async", new=AsyncMock(return_value=mock_response)):
        result = await _analyze_connections(
            {"title": "New", "content_snippet": "new content"},
            [{"title": "Other Article", "content_snippet": "other content"}],
        )
    assert len(result["related_articles"]) == 1
    assert result["related_articles"][0]["reason"] == "Both cover RAG"


# ── _write_article_note ──────────────────────────────────────────────────────

def test_write_article_note_creates_file(vault_path):
    from services.wiki_builder import _write_article_note

    item = {
        "title": "Test Article",
        "url": "https://example.com",
        "source_platform": "Blog",
        "added_at": "2026-05-20T10:00:00",
        "quick_read": "**核心内容**: test",
        "user_note": "great read",
    }
    concepts = [{"name": "RAG", "description": "def"}]
    _write_article_note(vault_path, item, concepts, [], "test-article")

    note_path = vault_path / "articles" / "test-article.md"
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "Test Article" in content
    assert "[[RAG]]" in content
    assert "great read" in content


def test_write_article_note_with_related(vault_path):
    from services.wiki_builder import _write_article_note

    item = {
        "title": "T", "url": "https://x.com", "source_platform": "Blog",
        "added_at": "2026-05-20", "quick_read": "summary", "user_note": "",
    }
    related = [{"item_id": "id-2", "title": "Other Article", "reason": "shared theme"}]
    _write_article_note(vault_path, item, [], related, "t-slug")

    content = (vault_path / "articles" / "t-slug.md").read_text()
    assert "[[other-article]]" in content
    assert "shared theme" in content


# ── _write_concept_note ──────────────────────────────────────────────────────

def test_write_concept_note_creates_file(vault_path):
    from services.wiki_builder import _write_concept_note

    concept = {"name": "RAG", "slug": "rag", "description": "Retrieval Augmented Generation"}
    _write_concept_note(vault_path, concept, ["article-one", "article-two"])

    note_path = vault_path / "concepts" / "rag.md"
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "article_count: 2" in content
    assert "[[article-one]]" in content


# ── process_article (integration) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_article_full_pipeline(monkeypatch, vault_path):
    import services.storage as s
    from services.wiki_builder import process_article

    item = {
        "id": "item-1",
        "title": "Learning Beyond Gradients",
        "url": "https://example.com/article",
        "source_platform": "Blog",
        "added_at": "2026-05-20T10:00:00",
        "quick_read": "**核心内容**: about learning without gradients",
        "user_note": "",
        "content_snippet": "This article discusses in-context learning and meta-learning approaches.",
        "business_opps": [],
        "rdev_opps": [],
    }
    monkeypatch.setattr(s, "get_manual_intel_item_by_id", lambda iid: item if iid == "item-1" else None)
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault_path))
    monkeypatch.setenv("WIKI_SYNTHESIS_THRESHOLD", "3")

    concepts_response = '[{"name": "In-Context Learning", "description": "Learning from examples in prompt"}]'
    connections_response = '{"related_articles": [], "additional_insights": ""}'

    call_count = 0

    async def mock_chat(messages, provider=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return concepts_response
        return connections_response

    monkeypatch.setattr("services.wiki_builder.chat_async", mock_chat)

    await process_article("item-1")

    # Article note written
    assert (vault_path / "articles" / "learning-beyond-gradients.md").exists()
    # Concept note written
    assert (vault_path / "concepts" / "in-context-learning.md").exists()
    # Index updated
    assert (vault_path / "_index.md").exists()
    # Data persisted
    node = s.get_wiki_article_node("item-1")
    assert node is not None
    assert "In-Context Learning" in node["concepts"]


@pytest.mark.asyncio
async def test_process_article_skips_if_no_quick_read(monkeypatch):
    import services.storage as s
    from services.wiki_builder import process_article

    item = {"id": "item-1", "title": "T", "quick_read": "", "content_snippet": "c"}
    monkeypatch.setattr(s, "get_manual_intel_item_by_id", lambda iid: item)

    called = []
    async def mock_chat(messages, provider=None):
        called.append(True)
        return "[]"

    monkeypatch.setattr("services.wiki_builder.chat_async", mock_chat)
    await process_article("item-1")
    assert called == []  # LLM not called when quick_read is empty
