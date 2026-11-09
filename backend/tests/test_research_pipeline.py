"""端到端流水线测试：假搜索后端 + 假 LLM，验证 plan→search→fetch→extract→verify→synthesize→validate 能串起来。

不触网、不调模型。重点验证三件事：
1. 各阶段产物按预期落盘；
2. 引文对不上的 claim 在抽取阶段就被丢弃，不进入核验；
3. 成稿里出现的引用都能映射回真实来源。
"""
import pytest

from services import storage
from services.research import models, pipeline, stages, store
from services.research.search_backend import SearchResult


class FakeBackend:
    name = "fake"

    def available(self):
        return True

    async def search(self, query, *, top_k=10, domains=None):
        # 正文要超过 pipeline.MIN_EXTRACT_CHARS，否则会被当成反爬空壳跳过
        filler = "这家公司近年在组织与产品上持续扩张，公开资料记录了多个团队的分工与协作方式。" * 6
        return [
            SearchResult(
                url="https://www.anthropic.com/company",
                title="Anthropic Company",
                snippet="官方介绍",
                source_tier="official",
                raw_content=filler + "Anthropic 在 2026 年 2 月约有 2,500 人，公司由 CEO Dario Amodei 领导。",
                engine="fake",
            ),
            SearchResult(
                url="https://www.bloomberg.com/news/x",
                title="Bloomberg 报道",
                snippet="媒体口径",
                source_tier="media",
                raw_content=filler + "Bloomberg 引用 Live Data 数据称员工数已超过 3,000 人。",
                engine="fake",
            ),
        ]


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fake_stages(monkeypatch):
    async def fake_plan(topic, questions, as_of):
        return models.Plan(
            thesis="Anthropic 正从实验室转向成规模公司",
            sections=[{"id": "s1", "heading": "组织规模", "purpose": "确认员工规模"}],
            sub_questions=[models.SubQuestion(
                id="q1", section="s1", question="现在有多少人？",
                queries=["Anthropic headcount", "Anthropic employees number"],
            )],
            entities=["Anthropic", "Dario Amodei"],
        )

    async def fake_extract(source, entities, *, start_index=0):
        if "anthropic.com" in source["url"]:
            return [
                models.Claim(id=f"c{start_index+1}", text="员工约 2,500 人",
                             quote="约有 2,500 人", source_id=source["id"], subject="Anthropic",
                             predicate="员工规模", as_of="2026-02"),
                # 引文对不上，应该被丢弃
                models.Claim(id=f"c{start_index+2}", text="员工约一万人",
                             quote="员工约一万人", source_id=source["id"], subject="Anthropic",
                             predicate="员工规模"),
            ]
        return [
            models.Claim(id=f"c{start_index+1}", text="员工超过 3,000 人",
                         quote="员工数已超过 3,000 人", source_id=source["id"], subject="Anthropic",
                         predicate="员工规模", as_of="2026-05"),
        ]

    async def fake_verify(claims, sources):
        return [
            models.Verdict(claim_ids=[claims[0]["id"]], verdict="single", note="官方口径"),
            models.Verdict(claim_ids=[claims[1]["id"]], verdict="single", note="媒体口径"),
        ]

    async def fake_synth(section, verdicts, claims, problems=None):
        ids = [cid for v in verdicts for cid in v["claim_ids"]]
        body = "\n".join(f"- 口径 {cid} 给出员工规模 [[{cid}]]" for cid in ids)
        return models.SectionDraft(
            section_id=section["id"], heading=section["heading"], markdown=body,
        )

    monkeypatch.setattr(stages, "plan_research", fake_plan)
    monkeypatch.setattr(stages, "extract_claims", fake_extract)
    monkeypatch.setattr(stages, "verify_claims", fake_verify)
    monkeypatch.setattr(stages, "synthesize_section", fake_synth)


async def test_pipeline_end_to_end(data_dir, fake_stages):
    run = store.create_run("Anthropic 组织研究", ["现在有多少人"], "2026-10-23")
    result = await pipeline.ResearchPipeline(run, backend=FakeBackend()).run_all()

    reloaded = store.get_run(run.id)
    assert reloaded.status == "done"
    assert reloaded.stage == "done"
    assert result["markdown"].startswith("# Anthropic 组织研究")

    # 两个来源都进了 store，且带着正文和分层
    sources = store.list_sources(run.id)
    assert len(sources) == 2
    assert {s["tier"] for s in sources} == {"official", "media"}
    assert all(s["text"] for s in sources)

    # 引文对不上的那条 claim 被丢弃
    claims = store.get_claims(run.id)
    assert len(claims) == 2
    assert all("一万人" not in c["text"] for c in claims)

    # 核验与成稿都落盘
    assert len(store.get_verification(run.id)) == 2
    report = store.get_report(run.id)
    assert "## 组织规模" in report["markdown"]
    assert "## 来源" in report["markdown"]

    metrics = store.coverage_metrics(run.id)
    assert metrics["sections"] == 1
    assert metrics["sources_by_tier"] == {"official": 1, "media": 1}


async def test_pipeline_marks_failed_run_on_plan_error(data_dir, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("模型不可用")

    monkeypatch.setattr(stages, "plan_research", boom)
    run = store.create_run("主题", [], "2026-10-23")

    with pytest.raises(RuntimeError):
        await pipeline.ResearchPipeline(run, backend=FakeBackend()).run_all()

    reloaded = store.get_run(run.id)
    assert reloaded.status == "failed"
    assert "模型不可用" in reloaded.error
    # 失败不删数据，run 记录仍在
    assert store.get_run(run.id) is not None
