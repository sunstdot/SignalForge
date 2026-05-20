import pytest


@pytest.fixture(autouse=True)
def isolated_wiki(monkeypatch, tmp_path):
    import services.storage as s
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr(s, "WIKI_DIR", wiki_dir)
    yield wiki_dir


def test_upsert_and_get_concept():
    from services.storage import upsert_wiki_concept, get_wiki_concepts

    c = upsert_wiki_concept("In-Context Learning", "in-context-learning", "A definition", "item-1")
    assert c["name"] == "In-Context Learning"
    assert c["slug"] == "in-context-learning"
    assert "item-1" in c["article_ids"]

    all_concepts = get_wiki_concepts()
    assert len(all_concepts) == 1


def test_upsert_concept_accumulates_article_ids():
    from services.storage import upsert_wiki_concept

    upsert_wiki_concept("RAG", "rag", "Retrieval Augmented Generation", "item-1")
    upsert_wiki_concept("RAG", "rag", "Retrieval Augmented Generation", "item-2")
    upsert_wiki_concept("RAG", "rag", "Retrieval Augmented Generation", "item-1")  # duplicate

    from services.storage import get_wiki_concepts
    concepts = get_wiki_concepts()
    assert len(concepts) == 1
    assert sorted(concepts[0]["article_ids"]) == ["item-1", "item-2"]


def test_delete_concept():
    from services.storage import upsert_wiki_concept, delete_wiki_concept, get_wiki_concepts

    upsert_wiki_concept("RAG", "rag", "def", "item-1")
    ok = delete_wiki_concept("rag")
    assert ok is True
    assert get_wiki_concepts() == []


def test_delete_nonexistent_concept():
    from services.storage import delete_wiki_concept
    assert delete_wiki_concept("does-not-exist") is False


def test_upsert_and_get_article_node():
    from services.storage import upsert_wiki_article_node, get_wiki_article_node, get_wiki_article_nodes

    node = upsert_wiki_article_node(
        item_id="item-1",
        slug="my-article",
        concepts=["RAG", "LLM"],
        related_articles=[{"item_id": "item-2", "title": "Other", "reason": "both cover RAG"}],
    )
    assert node["item_id"] == "item-1"
    assert node["slug"] == "my-article"
    assert "wiki_synced_at" in node

    fetched = get_wiki_article_node("item-1")
    assert fetched is not None
    assert fetched["concepts"] == ["RAG", "LLM"]

    all_nodes = get_wiki_article_nodes()
    assert len(all_nodes) == 1


def test_upsert_article_node_updates_existing():
    from services.storage import upsert_wiki_article_node, get_wiki_article_node

    first = upsert_wiki_article_node("item-1", "slug-v1", ["RAG"], [])
    second = upsert_wiki_article_node("item-1", "slug-v2", ["RAG", "LLM"], [])

    node = get_wiki_article_node("item-1")
    assert node["slug"] == "slug-v2"
    assert node["concepts"] == ["RAG", "LLM"]
    assert node["wiki_synced_at"] >= first["wiki_synced_at"]

    from services.storage import get_wiki_article_nodes
    assert len(get_wiki_article_nodes()) == 1


def test_get_wiki_article_node_missing():
    from services.storage import get_wiki_article_node
    assert get_wiki_article_node("nonexistent") is None
