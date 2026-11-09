"""参考链接学习 API：样本保存、分析、学习生效、试找、停用与反馈（无网络/无 LLM）。"""
import pytest
from fastapi.testclient import TestClient

from main import app
from services import signal_learning as learning
from services import storage


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    (tmp_path / "signal_learning").mkdir(parents=True, exist_ok=True)

    async def fake_fetch(url):
        return {"title": "参考标题", "content": "用 Agent 整理客服记录，发现高频问题", "fetch_ok": True, "reason": ""}

    async def fake_analyze(title, content, user_reason, user_wants):
        return {
            "ok": True, "topic": "Agent 在客服中的应用", "scenario": "整理客服记录",
            "contribution_type": "method", "contribution": "用 Agent 整理记录并发现高频问题",
            "value_reason": user_reason or "包含完整过程与成本信息",
            "value_reason_source": "user" if user_reason else "inferred",
            "evidence_forms": ["process", "cost"],
            "search_clues": [{"query": "agent 客服 高频问题", "subreddits": ["CustomerService"], "handles": []}],
            "uncertain": "",
        }

    async def fake_similar(reference_id, limit=3):
        return {
            "status": "ok", "reference": learning.get_reference_by_id(reference_id),
            "query": "agent 客服 高频问题", "subreddits": ["CustomerService"], "handles": [],
            "search_status": "ok", "search_error": "", "found": 1,
            "recommendations": [{
                "id": "x1", "title": "销售线索 agent 实操", "url": "https://example.com/x1",
                "summary": "完整流程与成本", "original_content": "流程 成本", "metadata": {},
                "match": {"similarity": "value"},
                "recommend_reason": "因你提供的参考信息而推荐：同样包含完整过程（价值相似）",
            }],
        }

    monkeypatch.setattr(learning, "fetch_reference_content", fake_fetch)
    monkeypatch.setattr(learning, "analyze_reference_content", fake_analyze)
    monkeypatch.setattr(learning, "find_similar_for_reference", fake_similar)
    return TestClient(app)


def test_create_reference_distinguishes_save_analysis_learning_search(client):
    resp = client.post("/api/signal-learning/references", json={
        "url": "https://example.com/ref", "user_reason": "包含完整过程和成本", "user_wants": "",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["sample_saved"] is True
    assert data["analysis_complete"] is True
    assert data["learning_active"] is True
    assert data["similar"]["status"] == "ok"
    assert data["similar"]["found"] == 1
    assert data["reference"]["analysis"]["value_reason_source"] == "user"


def test_inferred_reason_is_not_disguised_as_user_preference(client):
    resp = client.post("/api/signal-learning/references", json={
        "url": "https://example.com/ref2", "user_reason": "", "user_wants": "",
    })
    data = resp.json()
    assert data["reference"]["analysis"]["value_reason_source"] == "inferred"
    assert data["similar"]["inferred_reason"] is True


def test_preferences_are_checkable_and_disable_updates(client):
    created = client.post("/api/signal-learning/references", json={
        "url": "https://example.com/ref", "user_reason": "包含完整过程", "user_wants": "",
    }).json()
    ref_id = created["sample_id"]

    prefs = client.get("/api/signal-learning/preferences").json()
    assert ref_id in prefs["active_references"]
    assert any(p["form"] == "process" and ref_id in p["refs"] for p in prefs["value_patterns"])

    resp = client.post(f"/api/signal-learning/references/{ref_id}/disable")
    assert resp.status_code == 200
    prefs2 = client.get("/api/signal-learning/preferences").json()
    assert ref_id not in prefs2["active_references"]

    client.post(f"/api/signal-learning/references/{ref_id}/enable")
    prefs3 = client.get("/api/signal-learning/preferences").json()
    assert ref_id in prefs3["active_references"]


def test_feedback_is_recorded_and_reference_listed(client):
    created = client.post("/api/signal-learning/references", json={
        "url": "https://example.com/ref", "user_reason": "包含完整过程", "user_wants": "",
    }).json()
    ref_id = created["sample_id"]

    resp = client.post(f"/api/signal-learning/references/{ref_id}/feedback", json={
        "index": 0, "verdict": "topic_only",
    })
    assert resp.status_code == 200

    refs = client.get("/api/signal-learning/references").json()["references"]
    assert refs[0]["feedback"][0]["verdict"] == "topic_only"


def test_state_survives_refresh(client, tmp_path):
    created = client.post("/api/signal-learning/references", json={
        "url": "https://example.com/ref", "user_reason": "包含完整过程", "user_wants": "",
    }).json()
    ref_id = created["sample_id"]
    # 重新加载（模拟刷新页面/新任务）
    reloaded = learning.load_references(tmp_path / "signal_learning")
    assert any(r["id"] == ref_id and r["analysis"] for r in reloaded)
    snapshot = learning.load_preferences_snapshot(tmp_path / "signal_learning")
    assert ref_id in snapshot["active_references"]
