"""深度调研 API 测试：创建、查询、报告、来源、论断过滤、删除。

不触网、不调 LLM：后台执行被替换成空实现，测试只验证 API 契约与存储。
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from services import storage
from services.research import models, store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    import routers.research as research_router
    # 后台任务换成空实现，避免测试里真的跑流水线
    monkeypatch.setattr(research_router, "_execute", lambda run_id: None)
    monkeypatch.setattr(research_router, "_running", set())
    return TestClient(app)


def _seed_run(topic="Anthropic 组织研究"):
    run = store.create_run(topic, ["组织结构如何"], "2026-10-23")
    return run


def test_status_reports_degraded_without_tavily_key(client, monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("RESEARCH_SEARCH_BACKEND", "hn")
    body = client.get("/api/research/status").json()
    assert body["backend"] == "hn"
    assert body["degraded"] is True


def test_create_run_returns_created_run(client):
    resp = client.post("/api/research/runs", json={
        "topic": "Anthropic 组织研究",
        "questions": ["组织结构如何", "如何选拔人才"],
        "as_of": "2026-10-23",
    })
    assert resp.status_code == 201
    run = resp.json()["run"]
    assert run["topic"] == "Anthropic 组织研究"
    assert run["as_of"] == "2026-10-23"
    assert run["stage"] == "plan"


def test_create_run_rejects_blank_topic(client):
    resp = client.post("/api/research/runs", json={"topic": "   "})
    assert resp.status_code in (400, 422)


def test_list_runs_includes_created(client):
    run = _seed_run()
    body = client.get("/api/research/runs").json()
    assert any(item["id"] == run.id for item in body["runs"])


def test_get_run_404_for_unknown(client):
    assert client.get("/api/research/runs/nope").status_code == 404


def test_get_report_404_until_ready(client):
    run = _seed_run()
    assert client.get(f"/api/research/runs/{run.id}/report").status_code == 404

    store.save_report(run.id, models.Report(title="t", markdown="# 标题", metrics={"sections_total": 2}))
    body = client.get(f"/api/research/runs/{run.id}/report").json()
    assert body["report"]["markdown"] == "# 标题"
    assert body["metrics"]["sections_total"] == 2


def test_sources_hide_full_text_but_report_length(client):
    run = _seed_run()
    store.save_source(run.id, models.Source(
        id="src1", url="https://example.com/a", title="A",
        tier="official", fetch_status="ok", text="很长的正文" * 100,
    ))
    body = client.get(f"/api/research/runs/{run.id}/sources").json()
    source = body["sources"][0]
    assert source["id"] == "src1"
    assert source["chars"] > 0
    assert "text" not in source
    assert "很长的正文" not in str(body)


def test_claims_can_filter_by_verdict(client):
    run = _seed_run()
    store.save_claims(run.id, [
        models.Claim(id="c1", text="a", quote="a", source_id="src1"),
        models.Claim(id="c2", text="b", quote="b", source_id="src2"),
    ])
    store.save_verification(run.id, [
        models.Verdict(claim_ids=["c1"], verdict="confirmed"),
        models.Verdict(claim_ids=["c2"], verdict="single"),
    ])
    all_claims = client.get(f"/api/research/runs/{run.id}/claims").json()["claims"]
    assert len(all_claims) == 2

    confirmed = client.get(f"/api/research/runs/{run.id}/claims?verdict=confirmed").json()["claims"]
    assert [c["id"] for c in confirmed] == ["c1"]
    assert confirmed[0]["verdict"] == "confirmed"


def test_delete_run(client):
    run = _seed_run()
    assert client.delete(f"/api/research/runs/{run.id}").json()["deleted"] is True
    assert client.get(f"/api/research/runs/{run.id}").status_code == 404


def test_reverify_requires_existing_run(client):
    assert client.post("/api/research/runs/nope/reverify").status_code == 404


def test_reverify_rejects_run_without_claims(client):
    run = _seed_run()
    resp = client.post(f"/api/research/runs/{run.id}/reverify")
    assert resp.status_code == 400
    assert "论断" in resp.json()["detail"]


def test_reverify_schedules_stage_without_rerunning_pipeline(client, monkeypatch):
    run = _seed_run()
    store.save_claims(run.id, [models.Claim(id="c1", text="a", quote="a", source_id="src1")])

    called = []
    import routers.research as research_router
    monkeypatch.setattr(research_router, "_execute_stage", lambda rid, stage: called.append((rid, stage)))

    resp = client.post(f"/api/research/runs/{run.id}/reverify")
    assert resp.status_code == 200
    assert resp.json()["stage"] == "verify"
    assert called == [(run.id, "verify")]
