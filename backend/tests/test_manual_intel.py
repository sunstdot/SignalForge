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
