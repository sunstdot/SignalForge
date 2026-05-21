import pytest


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch, tmp_path):
    """Redirect MANUAL_INTEL_DIR to a temp directory for each test."""
    import services.storage as s
    new_dir = tmp_path / "manual_intel"
    new_dir.mkdir()
    monkeypatch.setattr(s, "MANUAL_INTEL_DIR", new_dir)
    yield new_dir


def test_create_and_get_item():
    from services.storage import create_manual_intel_item, get_manual_intel_item_by_id
    item = create_manual_intel_item({
        "url": "https://example.com/post",
        "title": "Test Article",
        "source_platform": "Blog",
        "user_note": "interesting",
        "content_snippet": "some content",
    })
    assert item["id"]
    assert item["title"] == "Test Article"
    assert item["source_platform"] == "Blog"
    assert item["user_note"] == "interesting"
    assert item["quick_read"] == ""
    assert item["business_opps"] == []
    assert item["rdev_opps"] == []

    found = get_manual_intel_item_by_id(item["id"])
    assert found is not None
    assert found["id"] == item["id"]


def test_get_items_returns_newest_first():
    from services.storage import create_manual_intel_item, get_manual_intel_items
    a = create_manual_intel_item({"url": "https://a.com", "title": "A"})
    b = create_manual_intel_item({"url": "https://b.com", "title": "B"})
    items = get_manual_intel_items()
    assert items[0]["id"] == b["id"]  # newest first
    assert items[1]["id"] == a["id"]


def test_filter_by_platform():
    from services.storage import create_manual_intel_item, get_manual_intel_items
    create_manual_intel_item({"url": "https://x.com/1", "title": "X post", "source_platform": "X"})
    create_manual_intel_item({"url": "https://reddit.com/r/1", "title": "Reddit post", "source_platform": "Reddit"})
    x_items = get_manual_intel_items(source_platform="X")
    assert len(x_items) == 1
    assert x_items[0]["source_platform"] == "X"


def test_update_item():
    from services.storage import create_manual_intel_item, update_manual_intel_item, get_manual_intel_item_by_id
    item = create_manual_intel_item({"url": "https://example.com", "title": "T"})
    updated = update_manual_intel_item(item["id"], {"quick_read": "summary here"})
    assert updated["quick_read"] == "summary here"
    # Persisted
    found = get_manual_intel_item_by_id(item["id"])
    assert found["quick_read"] == "summary here"


def test_delete_item():
    from services.storage import create_manual_intel_item, delete_manual_intel_item, get_manual_intel_item_by_id
    item = create_manual_intel_item({"url": "https://example.com", "title": "T"})
    ok = delete_manual_intel_item(item["id"])
    assert ok is True
    assert get_manual_intel_item_by_id(item["id"]) is None


def test_delete_nonexistent_returns_false():
    from services.storage import delete_manual_intel_item
    assert delete_manual_intel_item("nonexistent-id") is False


from fastapi.testclient import TestClient


@pytest.fixture
def client(isolated_storage, monkeypatch):
    import sys
    # Re-import app fresh so routers are reloaded with correct module references
    for mod in list(sys.modules.keys()):
        if mod.startswith("routers") or mod.startswith("services") or mod == "main":
            del sys.modules[mod]
    from main import app
    # Re-apply storage isolation to the freshly imported services.storage
    import services.storage as s
    monkeypatch.setattr(s, "MANUAL_INTEL_DIR", isolated_storage)
    return TestClient(app)


def test_get_items_empty(client):
    resp = client.get("/api/manual-intel")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_get_item_not_found(client):
    resp = client.get("/api/manual-intel/does-not-exist")
    assert resp.status_code == 404


def test_delete_item_not_found(client):
    resp = client.delete("/api/manual-intel/does-not-exist")
    assert resp.status_code == 404


def test_create_and_list_and_delete(client, monkeypatch):
    async def fake_fetch(url):
        return "Fake Title", "Fake content snippet"

    import routers.manual_intel as mi
    monkeypatch.setattr(mi, "_fetch_url_content", fake_fetch)

    async def fake_quick_read(item_id):
        pass
    monkeypatch.setattr(mi, "_run_quick_read", fake_quick_read)

    resp = client.post("/api/manual-intel", json={
        "url": "https://example.com/article",
        "source_platform": "Blog",
        "user_note": "great read",
    })
    assert resp.status_code == 201
    item = resp.json()
    assert item["title"] == "Fake Title"
    assert item["user_note"] == "great read"
    item_id = item["id"]

    # List
    resp = client.get("/api/manual-intel")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1

    # Get single
    resp = client.get(f"/api/manual-intel/{item_id}")
    assert resp.status_code == 200

    # Delete
    resp = client.delete(f"/api/manual-intel/{item_id}")
    assert resp.status_code == 200

    resp = client.get("/api/manual-intel")
    assert resp.json() == {"items": []}


def test_reanalyze_item(client, monkeypatch):
    import routers.manual_intel as mi

    async def fake_fetch(url):
        return "Title", "Snippet"

    async def fake_quick_read(item_id):
        pass

    monkeypatch.setattr(mi, "_fetch_url_content", fake_fetch)
    monkeypatch.setattr(mi, "_run_quick_read", fake_quick_read)

    # Create an item
    resp = client.post("/api/manual-intel", json={"url": "https://example.com"})
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    # Reanalyze — only resets quick_read, leaves business/rdev intact
    resp = client.post(f"/api/manual-intel/{item_id}/reanalyze")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Reanalyze non-existent item
    resp = client.post("/api/manual-intel/does-not-exist/reanalyze")
    assert resp.status_code == 404


def test_generate_business_and_rdev(client, monkeypatch):
    import routers.manual_intel as mi

    async def fake_fetch(url):
        return "Title", "Snippet"

    async def fake_quick_read(item_id):
        pass

    async def fake_generate_business(item):
        return [{"opportunity_title": "Test Biz", "core_insight": "insight"}]

    async def fake_generate_rdev(item):
        return [{"type": "研发提效", "title": "Test Rdev"}]

    monkeypatch.setattr(mi, "_fetch_url_content", fake_fetch)
    monkeypatch.setattr(mi, "_run_quick_read", fake_quick_read)
    monkeypatch.setattr(mi, "_generate_business_opps", fake_generate_business)
    monkeypatch.setattr(mi, "_generate_rdev_opps", fake_generate_rdev)

    resp = client.post("/api/manual-intel", json={"url": "https://example.com"})
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    # Generate business
    resp = client.post(f"/api/manual-intel/{item_id}/generate-business")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["business_opps"]) == 1
    assert data["business_opps"][0]["opportunity_title"] == "Test Biz"

    # Generate rdev
    resp = client.post(f"/api/manual-intel/{item_id}/generate-rdev")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rdev_opps"]) == 1
    assert data["rdev_opps"][0]["title"] == "Test Rdev"

    # 404 for non-existent
    resp = client.post("/api/manual-intel/does-not-exist/generate-business")
    assert resp.status_code == 404
    resp = client.post("/api/manual-intel/does-not-exist/generate-rdev")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_quick_read_triggers_wiki(monkeypatch, isolated_storage):
    """wiki process_article is called after quick_read succeeds, and wiki failure does not affect quick_read save."""
    from services.storage import create_manual_intel_item, get_manual_intel_item_by_id
    import routers.manual_intel as mi

    item = create_manual_intel_item({
        "url": "https://example.com",
        "title": "Test Article",
        "content_snippet": "some content",
    })

    wiki_called = []

    async def mock_chat(messages, provider=None):
        return "summary text"

    async def mock_process(item_id):
        wiki_called.append(item_id)

    monkeypatch.setattr(mi, "chat_async", mock_chat)
    import services.wiki_builder as wb
    monkeypatch.setattr(wb, "process_article", mock_process)

    await mi._run_quick_read(item["id"])

    # quick_read should be saved
    updated = get_manual_intel_item_by_id(item["id"])
    assert updated["quick_read"] == "summary text"
    # wiki should have been called
    assert item["id"] in wiki_called


@pytest.mark.asyncio
async def test_run_quick_read_wiki_failure_does_not_affect_quick_read(monkeypatch, isolated_storage):
    """A wiki failure after quick_read should not prevent quick_read from being saved."""
    from services.storage import create_manual_intel_item, get_manual_intel_item_by_id
    import routers.manual_intel as mi

    item = create_manual_intel_item({
        "url": "https://example.com",
        "title": "Test Article",
        "content_snippet": "some content",
    })

    async def mock_chat(messages, provider=None):
        return "summary text"

    async def mock_process_fail(item_id):
        raise RuntimeError("wiki failed")

    monkeypatch.setattr(mi, "chat_async", mock_chat)
    import services.wiki_builder as wb
    monkeypatch.setattr(wb, "process_article", mock_process_fail)

    # Should not raise
    await mi._run_quick_read(item["id"])

    # quick_read should still be saved despite wiki failure
    updated = get_manual_intel_item_by_id(item["id"])
    assert updated["quick_read"] == "summary text"
