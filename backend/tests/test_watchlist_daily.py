import json
from datetime import date

import pytest

from backend.services import collector, last30days_importer as importer, watchlist_daily


def _candidate(post_id, published_at):
    return {
        "title": f"Agent idea {post_id}", "url": f"https://x.com/builder/status/{post_id}",
        "source": "x", "final_score": 40,
        "source_items": [{"source": "x", "published_at": published_at, "body": "New builder workflow"}],
    }


def test_daily_import_uses_ingestion_day_but_preserves_original_publication(tmp_path, monkeypatch):
    report = {"topic": "AI agent", "range_to": "2026-10-10", "ranked_candidates": [
        _candidate("new", "2026-10-09T18:00:00Z"),
        _candidate("old", "2026-09-30T18:00:00Z"),
        _candidate("no-date", None),
    ]}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    saved = []
    monkeypatch.setattr(importer, "store_content_items", lambda items: saved.extend(items) or len(items))

    count = importer.import_last30days_file(path, collected_on="2026-10-10", lookback_days=2)

    assert count == 1
    assert saved[0]["created_at"] == "2026-10-10"
    assert saved[0]["date"] == "2026-10-09"
    assert saved[0]["published_at"] == "2026-10-09"
    assert saved[0]["metadata"]["origin"] == "last30days"
    assert saved[0]["metadata"]["daily_watchlist"] is True
    assert importer.parse_last30days_json(path.read_text())[1]["created_at"] == "2026-09-30"


def test_daily_import_skips_posts_already_seen_yesterday(tmp_path, monkeypatch):
    report = {"topic": "AI agent", "range_to": "2026-10-10", "ranked_candidates": [
        _candidate("same", "2026-10-09T18:00:00Z"),
    ]}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    prior_id = importer.parse_last30days_json(path.read_text())[0]["id"]
    monkeypatch.setattr(importer, "_load_content_file", lambda day: [{"id": prior_id}] if day == "2026-10-09" else [], raising=False)
    saved = []
    monkeypatch.setattr(importer, "store_content_items", lambda items: saved.extend(items) or len(items))
    assert importer.import_last30days_file(path, collected_on="2026-10-10") == 0
    assert saved == []


def test_watchlist_entry_counts_as_daily_but_interactive_search_does_not(monkeypatch):
    from backend.services import storage
    monkeypatch.setattr(storage, "_load_content_file", lambda date: [{"metadata": {"origin": "last30days", "daily_watchlist": True}}])
    assert storage._has_daily_content("2026-10-10")
    monkeypatch.setattr(storage, "_load_content_file", lambda date: [{"metadata": {"origin": "last30days"}}])
    assert not storage._has_daily_content("2026-10-10")


def test_watchlist_continues_after_one_topic_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(watchlist_daily, "WATCHLIST_DIR", tmp_path, raising=False)
    calls = []

    def fake_run(topic, **kwargs):
        calls.append((topic, kwargs))
        if topic == "broken":
            raise RuntimeError("unavailable")
        return 2

    monkeypatch.setattr(watchlist_daily, "run_last30days_via_wingsbot", fake_run)
    assert watchlist_daily.run_watchlist_daily(["broken", "AI agent"], "2026-10-10") == 2
    assert calls == [
        ("broken", {"collected_on": "2026-10-10", "lookback_days": 2}),
        ("AI agent", {"collected_on": "2026-10-10", "lookback_days": 2}),
    ]


def test_watchlist_does_not_repeat_successful_topics_on_same_day(monkeypatch, tmp_path):
    monkeypatch.setattr(watchlist_daily, "WATCHLIST_DIR", tmp_path, raising=False)
    calls = []

    def fake_run(topic, **kwargs):
        calls.append(topic)
        return 1

    monkeypatch.setattr(watchlist_daily, "run_last30days_via_wingsbot", fake_run)
    assert watchlist_daily.run_watchlist_daily(["AI agent"], "2026-10-10") == 1
    assert watchlist_daily.run_watchlist_daily(["AI agent"], "2026-10-10") == 0
    assert calls == ["AI agent"]


@pytest.mark.asyncio
async def test_collector_runs_watchlist_only_for_current_collection(monkeypatch):
    calls = []

    async def fake_fetch(*args, **kwargs):
        return []

    monkeypatch.setattr(collector, "fetch_all_sources", fake_fetch)
    monkeypatch.setattr(collector, "load_config", lambda: {"sources": {"watchlist": {
        "enabled": True, "topics": ["AI agent"], "accounts": ["@builder"]
    }}})
    monkeypatch.setattr(collector, "store_content_items", lambda items: 0)
    monkeypatch.setattr(collector, "run_watchlist_daily", lambda topics, day: calls.append((topics, day)) or 1, raising=False)
    await collector.run_collection("2026-09-01")
    assert calls == []
    await collector.run_collection(date.today().isoformat())
    assert calls == [(["AI agent", "@builder"], date.today().isoformat())]


def test_x_handle_topic_explicitly_requests_targeted_search():
    prompt = importer._build_wingsbot_prompt("@builder")
    assert "--x-handle builder" in prompt
