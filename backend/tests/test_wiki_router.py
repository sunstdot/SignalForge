import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    from tests.module_isolation import isolated_app_modules

    with isolated_app_modules():
        import services.storage as s
        wiki_dir = tmp_path / "wiki"
        wiki_dir.mkdir()
        mi_dir = tmp_path / "manual_intel"
        mi_dir.mkdir()
        monkeypatch.setattr(s, "WIKI_DIR", wiki_dir)
        monkeypatch.setattr(s, "MANUAL_INTEL_DIR", mi_dir)

        from main import app
        from fastapi.testclient import TestClient
        yield TestClient(app)


def test_get_status_empty(client):
    resp = client.get("/api/wiki/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["concept_count"] == 0
    assert data["article_count"] == 0
    assert data["last_synced_at"] is None


def test_list_concepts_empty(client):
    resp = client.get("/api/wiki/concepts")
    assert resp.status_code == 200
    assert resp.json() == {"concepts": []}


def test_delete_concept_not_found(client):
    resp = client.delete("/api/wiki/concept/does-not-exist")
    assert resp.status_code == 404


def test_delete_concept_success(client):
    from services.storage import upsert_wiki_concept
    upsert_wiki_concept("RAG", "rag", "def", "item-1")

    resp = client.delete("/api/wiki/concept/rag")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp2 = client.get("/api/wiki/concepts")
    assert resp2.json() == {"concepts": []}


def test_status_reflects_data(client):
    from services.storage import upsert_wiki_concept, upsert_wiki_article_node
    upsert_wiki_concept("RAG", "rag", "def", "item-1")
    upsert_wiki_article_node("item-1", "article-1", ["RAG"], [])

    resp = client.get("/api/wiki/status")
    data = resp.json()
    assert data["concept_count"] == 1
    assert data["article_count"] == 1
    assert data["last_synced_at"] is not None


def test_sync_returns_ok(client, monkeypatch):
    import services.wiki_builder as wb
    called = []

    async def mock_process(item_id):
        called.append(item_id)

    monkeypatch.setattr(wb, "process_article", mock_process)

    resp = client.post("/api/wiki/sync/item-123")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # Give the background task time to run
    import asyncio, time
    time.sleep(0.1)
    assert "item-123" in called


def test_rebuild_returns_ok(client, monkeypatch):
    from services.storage import create_manual_intel_item
    create_manual_intel_item({"url": "https://a.com", "title": "A"})

    import services.wiki_builder as wb
    async def mock_process(item_id):
        pass
    monkeypatch.setattr(wb, "process_article", mock_process)

    resp = client.post("/api/wiki/rebuild")
    assert resp.status_code == 200
    assert "Rebuilding wiki" in resp.json()["message"]
