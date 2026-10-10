from backend.services import briefing_generator
from backend.services.signal_feed import build_signal_feed


def _item(identifier, source_type, score, source=None, **extra):
    return {"id": identifier, "title": f"Title {identifier}", "url": f"https://example.com/{identifier}",
            "source": source or source_type, "source_type": source_type,
            "relevance_score": score, "created_at": "2026-10-10", **extra}


def test_signal_feed_filters_pr_and_duplicates_but_keeps_original_content():
    items = [
        _item("pr", "blog", 8, "Google AI Blog", content_bucket="corporate"),
        _item("launch", "blog", 10, "Google DeepMind Blog", content_bucket="product_launch"),
        _item("duplicate", "blog", 10, "Google AI Blog", content_bucket="product_launch", dup_of="launch"),
        _item("paper", "paper", 8),
        _item("x", "x", 8, summary="A builder found a new use case", metadata={"engagement": "54 likes", "author": "builder"}),
    ]
    saved = len(items)
    feed = build_signal_feed(items, {"paper": "**值得关注**：可用于评估 agent 的新方法"}, limit=3)
    assert feed["total"] == 3
    assert set(i["id"] for i in feed["inspiration"] + feed["execution"]) == {"launch", "paper", "x"}
    assert feed["execution"][0]["so_what"] == "可用于评估 agent 的新方法"
    assert any("54 likes" in i["why"] for i in feed["inspiration"])
    assert len(items) == saved


def test_generic_rss_does_not_crowd_out_ai_builder_signals():
    items = [
        _item("bookshelves", "rss", 9, "Design Blog", summary="My favorite design bookshelves"),
        _item("agent-tools", "rss", 8, "Builder Blog", summary="Agent tools and LLM workflows for developers"),
        _item("hn-digest", "hackernews", 9, "HackerNews Daily", summary="Top stories roundup"),
    ]
    feed = build_signal_feed(items)
    assert [i["id"] for i in feed["inspiration"]] == ["agent-tools"]


def test_signal_feed_has_global_15_item_limit_and_source_diversity():
    items = [_item(f"n{i}", "rss", 9, "One Newsletter", summary="LLM agent news") for i in range(30)]
    items += [_item(f"x{i}", "x", 8, "X", metadata={"author": f"author{i}"}) for i in range(7)]
    items += [_item(f"p{i}", "paper", 8, f"Paper {i}") for i in range(7)]
    feed = build_signal_feed(items, limit=15)
    ids = [i["id"] for i in feed["inspiration"] + feed["execution"]]
    assert len(ids) == feed["total"] == 15
    assert sum(i.startswith("n") for i in ids) <= 2
    assert len(feed["inspiration"]) >= 5
    assert len(feed["execution"]) >= 5


def test_briefing_exposes_signal_feed_without_losing_full_items(monkeypatch):
    items = [
        _item("paper", "paper", 8),
        _item("x", "x", 9, summary="New AI product concept"),
    ]
    monkeypatch.setattr(briefing_generator, "_load_content_file", lambda date: items)
    monkeypatch.setattr(briefing_generator, "get_all_dates", lambda: ["2026-10-10"])
    monkeypatch.setattr(briefing_generator, "save_briefing_file", lambda data: None)
    monkeypatch.setattr(briefing_generator, "load_quick_reads", lambda date: {}, raising=False)
    briefing = briefing_generator.generate_briefing_for_date("2026-10-10")
    assert len(briefing["items"]) == 2
    assert briefing["signals"]["total"] == 2
    assert briefing["signals"]["inspiration"][0]["id"] == "x"
