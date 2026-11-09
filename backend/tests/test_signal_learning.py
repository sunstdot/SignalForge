"""参考链接学习：价值特征提取、偏好聚合、试找与筛选联动（可控样本，无网络）。"""
import pytest

from backend.services import signal_learning as learning
from backend.services import storage


@pytest.fixture
def learning_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    (tmp_path / "signal_learning").mkdir(parents=True, exist_ok=True)
    return tmp_path / "signal_learning"


def _analysis(**overrides):
    base = {
        "topic": "Agent 在客服和用户反馈中的应用",
        "scenario": "团队整理客服记录，发现高频问题",
        "contribution_type": "method",
        "contribution": "用 Agent 整理客服记录，发现高频问题，并展示操作流程、失败案例和成本",
        "value_reason": "包含完整过程、失败分析和成本信息的真实实践",
        "value_reason_source": "user",
        "evidence_forms": ["process", "failure", "cost"],
        "search_clues": [{"query": "AI agent 客服记录 高频问题", "subreddits": ["CustomerService"], "handles": []}],
        "uncertain": "",
    }
    base.update(overrides)
    return base


def _reference(ref_id, **overrides):
    base = {
        "id": ref_id, "url": f"https://example.com/{ref_id}", "title": f"参考 {ref_id}",
        "user_reason": "包含完整过程、失败案例和成本信息", "user_wants": "",
        "content_snippet": "用 Agent 整理客服记录，发现高频问题", "status": "active",
        "analysis_status": "complete", "analysis": _analysis(), "feedback": [],
    }
    base.update(overrides)
    return base


# ── 价值特征提取与匹配 ──

def test_value_features_are_checkable_and_topic_agnostic():
    text = "我们用 agent 处理销售线索：先跑清洗流程，踩过的坑包括限流，成本大约每千条 0.3 元。"
    matched = learning.match_evidence_forms(text, ["process", "failure", "cost"])
    assert "process" in matched and "failure" in matched and "cost" in matched
    # 只提同一品牌但没有实质价值特征的宣传帖，不命中价值特征。
    promo = "Acme Agent 现已发布，AI 很有潜力，值得关注。"
    assert learning.match_evidence_forms(promo, ["process", "failure", "cost"]) == {}


def test_same_brand_without_value_content_is_not_ranked():
    ref = _reference("r1")
    candidate = {
        "id": "promo", "title": "Acme Agent 发布", "url": "https://x.com/acme/status/1",
        "summary": "Acme Agent 现已发布，AI 很有潜力。", "original_content": "Acme Agent 现已发布。",
        "metadata": {},
    }
    result = learning.rank_candidates([candidate], ref)
    # 泛化领域词（agent/ai）不构成主题相似；只有品牌名的宣传帖不会入选。
    assert result == []


def test_different_topic_with_similar_value_features_is_discovered():
    ref = _reference("r1")  # 主题：客服记录；价值特征：过程/失败/成本
    candidate = {
        "id": "sales", "title": "用 agent 处理销售线索的实操", "url": "https://example.com/sales",
        "summary": "完整流程和踩坑记录，成本也列出来了。",
        "original_content": "我们跑销售线索的流程，遇到限流坑，成本每千条 0.5 元。",
        "metadata": {},
    }
    results = learning.rank_candidates([candidate], ref, limit=3)
    assert len(results) == 1
    assert results[0]["match"]["similarity"] == "value"
    assert "价值相似" in results[0]["recommend_reason"]


def test_user_reason_overrides_inferred_reason_in_prompt():
    prompt = learning.build_analysis_prompt("标题", "正文", "用户明确认为有价值的原因", "")
    assert "用户明确认为有价值的原因" in prompt
    assert "user 或 inferred" in prompt


def test_analyze_normalizes_value_reason_source(monkeypatch):
    async def fake_chat(messages, **kwargs):
        return ('{"topic":"t","scenario":"s","contribution_type":"method","contribution":"c",'
                '"value_reason":"推测原因","value_reason_source":"user","evidence_forms":["process"],'
                '"search_clues":[{"query":"q","subreddits":[],"handles":[]}],"uncertain":""}')

    monkeypatch.setattr(learning, "chat_async", fake_chat)

    import asyncio
    # 用户未填写原因：即使 LLM 误报 user，也应降级为 inferred。
    result = asyncio.run(learning.analyze_reference_content("t", "c", "", ""))
    assert result["ok"] is True, result
    assert result["value_reason_source"] == "inferred"


# ── 偏好聚合与停用 ──

def test_preferences_trace_references_and_disable_updates(learning_dir):
    learning.save_references([
        _reference("r1"),
        _reference("r2", analysis=_analysis(
            topic="Agent 处理销售线索",
            search_clues=[{"query": "agent 销售线索 流程", "subreddits": [], "handles": []}],
        )),
    ])
    prefs = learning.refresh_preferences(learning_dir)
    assert "r1" in prefs["active_references"] and "r2" in prefs["active_references"]
    # 停用 r1 后，r2 支持的偏好仍然保留，r1 的专属主题被移除。
    learning.set_reference_status("r1", "disabled", learning_dir)
    prefs2 = learning.refresh_preferences(learning_dir)
    assert "r1" not in prefs2["active_references"]
    assert "r2" in prefs2["active_references"]
    assert all("r1" not in clue.get("refs", []) for clue in prefs2["search_clues"])


def test_single_sample_has_limited_influence(learning_dir):
    learning.save_references([_reference("r1")])
    prefs = learning.refresh_preferences(learning_dir)
    # 一条样本只产生有限影响：检索线索数量受样本自身限制，不会凭空扩展。
    assert len(prefs["search_clues"]) == 1
    assert prefs["themes"][0]["weight"] == 1


def test_boost_only_from_value_features_not_topic_keywords():
    prefs = {
        "themes": [{"text": "Acme Agent", "weight": 1, "refs": ["r1"]}],
        "value_patterns": [{"form": "process", "weight": 1, "refs": ["r1"]},
                           {"form": "failure", "weight": 1, "refs": ["r1"]}],
    }
    promo = {"title": "Acme Agent 发布", "summary": "Acme Agent 很有潜力", "original_content": "Acme Agent 发布"}
    process = {"title": "实操流程", "summary": "完整流程和踩坑", "original_content": "我们跑流程，踩坑了"}
    promo_boost = learning.learned_boost(promo, prefs)
    process_boost = learning.learned_boost(process, prefs)
    # 价值特征命中的提升远大于单纯主题命中。
    assert process_boost["boost"] > promo_boost["boost"]
    assert "process" in process_boost["matched_forms"]
    assert promo_boost["matched_forms"] == {}


# ── 试找类似信息 ──

@pytest.mark.asyncio
async def test_find_similar_uses_injected_search_and_returns_reasons(learning_dir):
    learning.save_references([_reference("r1")])

    async def fake_search(query, subreddits, handles):
        return {"status": "ok", "items": [{
            "id": "x1", "title": "用 agent 处理销售线索", "url": "https://example.com/x1",
            "summary": "完整流程、踩坑记录和成本。", "original_content": "流程 坑 成本", "metadata": {},
        }], "error": ""}

    result = await learning.find_similar_for_reference("r1", limit=3, search_fn=fake_search,
                                                       cache_dir=learning_dir)
    assert result["status"] == "ok"
    assert result["search_status"] == "ok"
    assert result["found"] == 1
    assert result["query"] == "AI agent 客服记录 高频问题"
    assert "价值相似" in result["recommendations"][0]["recommend_reason"]
    # 学习结果落盘可追溯。
    saved = learning.get_reference_by_id("r1", learning_dir)
    assert saved["last_similar"]["found"] == 1


@pytest.mark.asyncio
async def test_find_similar_distinguishes_no_match_from_search_failure(learning_dir):
    learning.save_references([_reference("r1")])

    async def empty_search(query, subreddits, handles):
        return {"status": "ok", "items": [], "error": ""}

    result = await learning.find_similar_for_reference("r1", search_fn=empty_search,
                                                       cache_dir=learning_dir)
    assert result["status"] == "no_match"
    assert result["found"] == 0
    # 现有来源覆盖不到时给出扩源建议，不宣称已完整覆盖。
    assert "扩" in result["suggestion"] or "补充" in result["suggestion"]

    async def failing_search(query, subreddits, handles):
        return {"status": "search_failed", "items": [], "error": "rate_limited"}

    result2 = await learning.find_similar_for_reference("r1", search_fn=failing_search,
                                                        cache_dir=learning_dir)
    assert result2["status"] == "search_failed"
    assert result2["search_error"] == "rate_limited"


# ── 状态持久化 ──

def test_state_survives_reload(learning_dir):
    learning.save_references([_reference("r1")])
    learning.refresh_preferences(learning_dir)
    # 重新加载（模拟刷新页面/新任务）
    refs = learning.load_references(learning_dir)
    assert refs[0]["id"] == "r1" and refs[0]["analysis"]["topic"]
    prefs = learning.load_preferences_snapshot(learning_dir)
    assert "r1" in prefs["active_references"]


def test_learned_watchlist_queries_follow_active_status(learning_dir):
    learning.save_references([_reference("r1")])
    learning.refresh_preferences(learning_dir)
    assert learning.learned_watchlist_queries(cache_dir=learning_dir) == ["AI agent 客服记录 高频问题"]

    learning.set_reference_status("r1", "disabled", learning_dir)
    learning.refresh_preferences(learning_dir)
    # 停用后，后续任务不再使用该线索。
    assert learning.learned_watchlist_queries(cache_dir=learning_dir) == []
