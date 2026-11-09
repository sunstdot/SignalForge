"""调研能力的单元测试：来源分层、引文校验、成稿校验、存储隔离。

不触网、不调 LLM。
"""
import json

import pytest

from services.research import models, search_backend, stages, store, validator


def _source(sid="src1", text="Anthropic 在 2026 年 2 月约有 2,500 人。", tier="firsthand"):
    return models.Source(id=sid, url=f"https://example.com/{sid}", title="t", tier=tier, text=text)


def _claim(cid="c1", quote="Anthropic 在 2026 年 2 月约有 2,500 人。", source_id="src1"):
    return models.Claim(id=cid, text="员工约 2500 人", quote=quote, source_id=source_id)


# ───────────────────────── 来源分层 ─────────────────────────

@pytest.mark.parametrize("url,tier", [
    ("https://www.anthropic.com/company", "official"),
    ("https://job-boards.greenhouse.io/anthropic", "official"),
    ("https://www.dwarkesh.com/p/dario-amodei-2", "firsthand"),
    ("https://www.youtube.com/watch?v=tivaWTTVRhY", "firsthand"),
    ("https://www.bloomberg.com/news/features/x", "media"),
    ("https://www.theinformation.com/articles/x", "media"),
    ("https://mp.weixin.qq.com/s/abc", "secondary"),
    ("https://unknown-site.example/x", "secondary"),
])
def test_classify_domain(url, tier):
    assert search_backend.classify_domain(url) == tier


def test_unknown_domain_defaults_to_secondary():
    # 域名不在任何名单里时按低估处理，避免把未知来源当权威
    assert search_backend.classify_domain("https://random.example/post") == "secondary"


# ───────────────────────── 引文校验 ─────────────────────────

def test_quote_verbatim_exact_match():
    text = "Bloomberg Businessweek 在同年 5 月引用 Live Data Technologies 数据称，员工数已超过 3,000 人。"
    assert stages.quote_is_verbatim("员工数已超过 3,000 人", text)


def test_quote_verbatim_tolerates_whitespace_and_quotes():
    text = 'Daniela Amodei 说，公司需要“不寻常的信念”。'
    assert stages.quote_is_verbatim('公司需要"不寻常的信念"', text)


def test_quote_verbatim_rejects_paraphrase():
    text = "公司约有 2,500 人。"
    assert not stages.quote_is_verbatim("公司大概有两千五百人", text)


def test_quote_verbatim_rejects_empty():
    assert not stages.quote_is_verbatim("", "anything")
    assert not stages.quote_is_verbatim("anything", "")


# ───────────────────────── 成稿校验 ─────────────────────────

def _verdicts(*claim_ids, verdict="confirmed"):
    return [{"claim_ids": list(claim_ids), "verdict": verdict, "supporters": list(claim_ids), "conflicts": [], "note": ""}]


def test_check_section_passes_with_cited_lines():
    claims = {"c1": _claim().as_dict()}
    sources = {"src1": _source().as_dict()}
    draft = {"section_id": "s1", "heading": "组织", "markdown": "- 员工约 2,500 人 [[c1]]"}
    ok, problems = validator.check_section(draft, claims, sources, _verdicts("c1"))
    assert ok, problems


def test_check_section_flags_uncited_conclusion_line():
    claims = {"c1": _claim().as_dict()}
    sources = {"src1": _source().as_dict()}
    draft = {"section_id": "s1", "heading": "组织", "markdown": "- 员工规模扩张很快，组织高度职能化。"}
    ok, problems = validator.check_section(draft, claims, sources, _verdicts("c1"))
    assert not ok
    assert any(p["type"] == "uncited_line" for p in problems)


def test_check_section_flags_unknown_claim():
    claims = {}
    sources = {}
    draft = {"section_id": "s1", "heading": "组织", "markdown": "- 某个结论 [[c99]]"}
    ok, problems = validator.check_section(draft, claims, sources, [])
    assert not ok
    assert any(p["type"] == "unknown_claim" for p in problems)


def test_check_section_flags_quote_not_in_source():
    claims = {"c1": _claim(quote="员工超过一万人").as_dict()}
    sources = {"src1": _source().as_dict()}
    draft = {"section_id": "s1", "heading": "组织", "markdown": "- 员工约一万人 [[c1]]"}
    ok, problems = validator.check_section(draft, claims, sources, _verdicts("c1"))
    assert not ok
    assert any(p["type"] == "quote_mismatch" for p in problems)


def test_check_section_flags_hidden_conflict():
    # 两个来源给出不同人数，正文只写了一个版本 → 判冲突未呈现
    sources = {
        "src1": _source("src1", "约有 2,500 人。").as_dict(),
        "src2": _source("src2", "已超过 3,000 人。").as_dict(),
    }
    claims = {
        "c1": _claim("c1", "约有 2,500 人。", "src1").as_dict(),
        "c2": _claim("c2", "已超过 3,000 人。", "src2").as_dict(),
    }
    draft = {"section_id": "s1", "heading": "组织", "markdown": "- 公司约有 2,500 人 [[c1]]"}
    ok, problems = validator.check_section(draft, claims, sources, _verdicts("c1", "c2", verdict="conflict"))
    assert not ok
    assert any(p["type"] == "conflict_hidden" for p in problems)


def test_check_section_ignores_conflict_cluster_not_mentioned_in_section():
    # 该节完全没引用这个冲突簇 → 说明这簇内容不属于本节，不能判为隐藏冲突
    sources = {
        "src1": _source("src1", "约有 2,500 人。").as_dict(),
        "src2": _source("src2", "已超过 3,000 人。").as_dict(),
    }
    claims = {
        "c1": _claim("c1", "约有 2,500 人。", "src1").as_dict(),
        "c2": _claim("c2", "已超过 3,000 人。", "src2").as_dict(),
        "c9": _claim("c9", "约有 2,500 人。", "src1").as_dict(),
    }
    draft = {"section_id": "s1", "heading": "组织", "markdown": "- 另一个不相关的事实 [[c9]]"}
    ok, problems = validator.check_section(draft, claims, sources, _verdicts("c1", "c2", verdict="conflict"))
    assert ok, problems
    assert not any(p["type"] == "conflict_hidden" for p in problems)


def test_check_section_flags_conflict_when_only_one_version_cited():
    sources = {
        "src1": _source("src1", "约有 2,500 人。").as_dict(),
        "src2": _source("src2", "已超过 3,000 人。").as_dict(),
    }
    claims = {
        "c1": _claim("c1", "约有 2,500 人。", "src1").as_dict(),
        "c2": _claim("c2", "已超过 3,000 人。", "src2").as_dict(),
    }
    draft = {"section_id": "s1", "heading": "组织", "markdown": "- 公司约有 2,500 人 [[c1]]"}
    ok, problems = validator.check_section(draft, claims, sources, _verdicts("c1", "c2", verdict="conflict"))
    assert not ok
    assert any(p["type"] == "conflict_hidden" for p in problems)


def test_check_section_flags_empty_draft():
    ok, problems = validator.check_section({"markdown": ""}, {}, {}, [])
    assert not ok
    assert problems[0]["type"] == "empty"


# ───────────────────────── 存储 ─────────────────────────

@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    from services import storage
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    return tmp_path


def test_create_and_load_run_is_isolated_under_research(data_dir):
    run = store.create_run("Anthropic 组织研究", ["组织结构如何", "如何选拔"], "2026-10-23")
    assert (data_dir / "research" / "runs" / run.id / "run.json").exists()
    loaded = store.get_run(run.id)
    assert loaded.topic == "Anthropic 组织研究"
    assert loaded.as_of == "2026-10-23"
    # 不污染既有数据目录
    assert not (data_dir / "briefings").exists()


def test_list_runs_reports_status(data_dir):
    run = store.create_run("主题", [], "2026-10-23")
    store.set_stage(run, "verify", "verified")
    runs = store.list_runs()
    assert runs[0]["id"] == run.id
    assert runs[0]["stage"] == "verify"


def test_coverage_metrics_counts_tiers_and_verdicts(data_dir):
    run = store.create_run("主题", [], "2026-10-23")
    store.save_source(run.id, _source("src1", tier="official"))
    store.save_source(run.id, _source("src2", tier="media"))
    store.save_claims(run.id, [_claim("c1"), _claim("c2", source_id="src2")])
    store.save_verification(run.id, [
        models.Verdict(claim_ids=["c1"], verdict="confirmed"),
        models.Verdict(claim_ids=["c2"], verdict="single"),
    ])
    metrics = store.coverage_metrics(run.id)
    assert metrics["sources_total"] == 2
    assert metrics["sources_by_tier"] == {"official": 1, "media": 1}
    assert metrics["claims_by_verdict"] == {"confirmed": 1, "single": 1, "conflict": 0}


def test_report_roundtrip(data_dir):
    run = store.create_run("主题", [], "2026-10-23")
    store.save_report(run.id, models.Report(title="主题", markdown="# 标题\n正文", metrics={"sections_total": 1}))
    report = store.get_report(run.id)
    assert report["markdown"] == "# 标题\n正文"
    assert report["metrics"]["sections_total"] == 1


def test_delete_run_removes_directory(data_dir):
    run = store.create_run("主题", [], "2026-10-23")
    assert store.delete_run(run.id)
    assert store.get_run(run.id) is None
    assert not store.delete_run(run.id)


def test_build_report_lists_only_fetched_sources(data_dir):
    sources = {
        "src1": _source("src1").as_dict(),
        "src2": models.Source(id="src2", url="https://x.example", title="坏来源", fetch_status="paywalled", text="").as_dict(),
    }
    claims = {"c1": _claim().as_dict()}
    drafts = [{"section_id": "s1", "heading": "组织", "markdown": "- 员工约 2,500 人 [[c1]]", "rejected": []}]
    markdown = validator.build_report("标题", "论点", drafts, claims, _verdicts("c1"), sources)
    assert "## 来源" in markdown
    assert "https://example.com/src1" in markdown
    assert "https://x.example" not in markdown
