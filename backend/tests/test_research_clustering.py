"""核验层聚类测试：归一化、分桶、跨来源选择、按簇核验的兜底行为。

不触网、不调 LLM。
"""
import pytest

from services.research import clustering, models, stages


def _claim(cid, subject, predicate, text="", source_id="src1"):
    return {
        "id": cid,
        "text": text or f"{subject} {predicate}",
        "quote": "quote",
        "source_id": source_id,
        "subject": subject,
        "predicate": predicate,
    }


# ───────────────────────── 归一化 ─────────────────────────

@pytest.mark.parametrize("left,right", [
    ("担任 CEO", "担任首席执行官"),
    ("担任 CEO", "is the CEO"),
    ("总部位于旧金山", " headquartered in"),
    ("成立于 2021 年", "was founded in"),
    ("员工数约 2500 人", "员工规模"),
    ("注册为公益公司", "is a public benefit corporation"),
])
def test_synonyms_normalize_together(left, right):
    assert clustering.normalize_predicate(left) == clustering.normalize_predicate(right)


def test_number_does_not_split_bucket():
    # 数字差异恰恰是要被判为冲突的对象，不能因为它分到不同桶
    a = clustering.normalize_predicate("员工数 2500 人")
    b = clustering.normalize_predicate("员工数 3000 人")
    assert a == b


def test_unrelated_predicates_stay_separate():
    a = clustering.normalize_predicate("担任 CEO")
    b = clustering.normalize_predicate("担任联合创始人")
    assert a != b


def test_subject_normalization_strips_articles_and_parentheticals():
    assert clustering.normalize_subject("The Anthropic") == clustering.normalize_subject("anthropic")
    assert clustering.normalize_subject("Anthropic (company)") == "anthropic"


# ───────────────────────── 分桶 ─────────────────────────

def test_same_fact_from_two_sources_forms_cross_source_cluster():
    claims = [
        _claim("c1", "Anthropic", "员工数约 2500 人", source_id="src1"),
        _claim("c2", "Anthropic", "员工规模", source_id="src2"),
    ]
    clusters = clustering.cluster_claims(claims)
    assert len(clusters) == 1
    assert clusters[0]["cross_source"] is True
    assert clusters[0]["claim_ids"] == ["c1", "c2"]


def test_same_source_repeat_is_not_cross_source():
    claims = [
        _claim("c1", "Anthropic", "员工规模", source_id="src1"),
        _claim("c2", "Anthropic", "员工数 2500 人", source_id="src1"),
    ]
    clusters = clustering.cluster_claims(claims)
    assert clusters[0]["cross_source"] is False


def test_missing_subject_and_predicate_stay_solo():
    claims = [
        _claim("c1", "", "", source_id="src1"),
        _claim("c2", "", "", source_id="src2"),
    ]
    clusters = clustering.cluster_claims(claims)
    assert len(clusters) == 2
    assert all(not c["cross_source"] for c in clusters)


def test_selection_prefers_cross_source():
    claims = [
        _claim("c1", "A", "员工规模", source_id="s1"),
        _claim("c2", "A", "员工规模", source_id="s2"),
        _claim("c3", "B", "总部位于", source_id="s3"),
        _claim("c4", "B", "总部位于", source_id="s3"),
    ]
    clusters = clustering.cluster_claims(claims)
    selected = clustering.select_for_verification(clusters)
    assert selected[0]["cross_source"] is True
    assert set(selected[0]["claim_ids"]) == {"c1", "c2"}


def test_selection_caps_cluster_count():
    # 构造 10 个跨来源簇，验证上限生效
    claims = [
        _claim(f"c{i}", f"S{i}", "员工规模", source_id=f"s{i}a")
        for i in range(10)
    ] + [
        _claim(f"d{i}", f"S{i}", "员工规模", source_id=f"s{i}b")
        for i in range(10)
    ]
    clusters = clustering.cluster_claims(claims)
    assert len([c for c in clusters if c["cross_source"]]) == 10
    assert len(clustering.select_for_verification(clusters, max_clusters=5)) == 5


def test_selection_skips_single_claim_single_source():
    # 一条论断且只有一个来源：没有可对照的第二方，不必花模型调用
    claims = [_claim(f"c{i}", f"S{i}", "员工规模", source_id=f"s{i}") for i in range(10)]
    clusters = clustering.cluster_claims(claims)
    assert clustering.select_for_verification(clusters) == []


# ───────────────────────── 按簇核验 ─────────────────────────

async def test_verify_claims_calls_model_once_per_cluster(monkeypatch):
    calls = []

    async def fake_chat(messages, system_prompt="", model=None, provider=None):
        calls.append(messages[0]["content"])
        return '[{"claim_ids": ["c1"], "verdict": "confirmed", "supporters": ["c1"], "conflicts": [], "note": "官方"}]'

    monkeypatch.setattr(stages, "chat_async", fake_chat)

    claims = [
        _claim("c1", "Anthropic", "总部位于", source_id="src1"),
        _claim("c2", "Anthropic", " headquartered in", source_id="src2"),
        _claim("c3", "Anthropic", "成立", source_id="src3"),   # 单来源，不应送核验
    ]
    verdicts = await stages.verify_claims(claims, {"src1": {"tier": "official"}, "src2": {"tier": "media"}, "src3": {"tier": "secondary"}})

    # 只有跨来源的那一个簇被送去核验
    assert len(calls) == 1
    assert "聚类主题" in calls[0]

    by_claim = {cid: v["verdict"] for v in (x.as_dict() for x in verdicts) for cid in v["claim_ids"]}
    assert by_claim["c1"] == "confirmed"
    # 单来源的没有送模型，标 single 且说明原因
    assert by_claim["c3"] == "single"


async def test_verify_claims_marks_unverified_with_reason(monkeypatch):
    async def fake_chat(messages, system_prompt="", model=None, provider=None):
        return "[]"   # 模型什么都没判

    monkeypatch.setattr(stages, "chat_async", fake_chat)
    claims = [_claim("c1", "Anthropic", "总部位于", source_id="src1")]
    verdicts = await stages.verify_claims(claims, {"src1": {"tier": "official"}})
    assert verdicts[0].verdict == "single"
    assert "单来源" in verdicts[0].note


async def test_verify_cluster_falls_back_on_llm_error(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("429 insufficient balance")

    monkeypatch.setattr(stages, "chat_async", boom)
    cluster = {"key": ["a", "b"], "claim_ids": ["c1", "c2"], "source_ids": ["s1", "s2"]}
    claims = {"c1": _claim("c1", "a", "b"), "c2": _claim("c2", "a", "b", "x", "s2")}
    verdicts = await stages.verify_cluster(cluster, claims, {})
    assert len(verdicts) == 2
    assert all(v.verdict == "single" for v in verdicts)


async def test_verify_claims_empty_input():
    assert await stages.verify_claims([], {}) == []
