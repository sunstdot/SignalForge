from backend.services import briefing_generator
from backend.services.signal_feed import build_signal_feed


def _item(identifier, source_type, score, source=None, **extra):
    return {"id": identifier, "title": f"Title {identifier}", "url": f"https://example.com/{identifier}",
            "source": source or source_type, "source_type": source_type,
            "relevance_score": score, "created_at": "2026-10-10", **extra}


def _quick_read(core="发布了可复用的 Agent 工作流，并给出实现方式。", insight="可以对照自己的自动化流程评估是否值得试用。"):
    return f"**核心内容**：{core}\n\n**值得关注**：{insight}"


def test_signal_requires_substantive_source_and_an_explanation_not_just_a_title():
    items = [
        _item("pr", "blog", 10, "AI Company", content_bucket="technical",
              summary="AI Company is an AI company.", original_content="AI Company is an AI company."),
        _item("headline", "hn", 10, title="Show HN: Agent on a calculator",
              summary="Show HN: Agent on a calculator", metadata={"volume": 500}),
        _item("unexplained", "rss", 10, "Builder Blog",
              summary="AI agent workflow with permission controls and an open reference implementation for developers."),
        _item("useful", "anthropic_blog", 8, "Anthropic",
              summary="Anthropic released an opt-in open-source scanner with recurring model-assisted vulnerability checks and examples.",
              original_content="The opt-in security scanner regularly checks open-source projects for vulnerabilities with AI."),
    ]
    # Historical quick reads may be present even for items with no actual source detail.
    quick_reads = {"pr": _quick_read(), "headline": _quick_read(), "useful": _quick_read()}
    feed = build_signal_feed(items, quick_reads)
    assert [i["id"] for i in feed["inspiration"] + feed["execution"]] == ["useful"]
    assert feed["execution"][0]["takeaway"] == "发布了可复用的 Agent 工作流，并给出实现方式。"
    assert feed["execution"][0]["so_what"] == "可以对照自己的自动化流程评估是否值得试用。"
    assert len(items) == 4  # 筛选不删原始数据


def test_low_engagement_x_is_excluded_even_when_quick_read_sounds_convincing():
    post = "A builder published a reproducible agent workflow with code, logs, failure cases, and a public benchmark."
    items = [
        _item("no-proof", "x", 10, title=post, summary=post,
              metadata={"author": "builder", "engagement": "0 likes, 1 replies", "volume": 1}),
        _item("credible", "x", 8, title=post, summary=post,
              metadata={"author": "other", "engagement": "27 likes, 5 replies", "volume": 32}),
    ]
    feed = build_signal_feed(items, {i["id"]: _quick_read() for i in items})
    assert feed["total"] == 1
    assert [i["id"] for i in feed["inspiration"]] == ["credible"]
    assert feed["inspiration"][0]["evidence"] == "27 likes, 5 replies"


def test_missing_quick_read_does_not_fill_the_daily_signal_quota():
    items = [_item(f"paper-{n}", "paper", 10,
                   original_content="An abstract describing the method, validation, results and limitations in detail.")
             for n in range(20)]
    assert build_signal_feed(items)["total"] == 0


def test_signal_includes_concrete_facts_from_cached_quick_read():
    item = _item("scanner", "anthropic_blog", 8, "Anthropic",
                 summary="Anthropic published an opt-in service that repeatedly scans open-source projects for security vulnerabilities.")
    quick_read = ("**核心内容**：Anthropic推出可选择加入的开源漏洞扫描服务，提供定期安全检查。\n\n"
                  "**关键信息**：\n- 项目需主动申请加入\n- 定期免费扫描开源代码\n- 源自 Project Glasswing\n\n"
                  "**值得关注**：维护开源项目时可检查是否符合加入条件。")
    card = build_signal_feed([item], {"scanner": quick_read})["execution"][0]
    assert card["facts"] == ["项目需主动申请加入", "定期免费扫描开源代码"]


def test_views_without_interaction_are_not_x_evidence():
    post = "A developer published a full agent workflow with code, benchmarks, failure analysis and an independent reproduction guide."
    item = _item("views", "x", 10, title=post, summary=post,
                 metadata={"volume": 2000, "engagement": "0 likes, 0 replies, 0 reposts, 2000 views"})
    assert build_signal_feed([item], {"views": _quick_read()})["total"] == 0


def test_malformed_x_engagement_does_not_break_the_entire_briefing():
    post = "A builder published an agent workflow with public source code, reproduction steps and measured benchmarks."
    item = _item("broken", "x", 10, title=post, summary=post,
                 metadata={"volume": 2000, "engagement": ", replies, 2 likes, 2000 views"})
    assert build_signal_feed([item], {"broken": _quick_read()})["total"] == 0


def test_unrelated_company_launch_and_mental_model_of_git_are_not_ai_signals():
    items = [
        _item("game", "blog", 10, "Google AI Blog", content_bucket="product_launch",
              title="Create custom games on Playground",
              summary="A new gaming platform lets you create and share browser games with your friends.",
              original_content="A new gaming platform lets you create and share browser games with your friends."),
        _item("git", "rss", 9, "Engineering Blog", title="On Git Refs",
              original_content="I recently improved my mental model of Git references and explain how remote refs work in two shell commands."),
    ]
    assert build_signal_feed(items, {i["id"]: _quick_read() for i in items})["total"] == 0


def test_model_word_is_not_enough_without_ai_context():
    generic = _item("generic", "rss", 9, "Engineering Blog", title="Mental models for Git",
                    original_content="Mental models for Git references can help developers understand branches and remotes in everyday workflows.")
    model_news = _item("model-news", "rss", 8, "Model Lab", title="A new multimodal model",
                       original_content="The new multimodal model accepts images and audio, and provides benchmarks and developer examples.")
    feed = build_signal_feed([generic, model_news], {i["id"]: _quick_read() for i in (generic, model_news)})
    assert [i["id"] for i in feed["inspiration"]] == ["model-news"]


def test_official_site_boilerplate_is_not_enough_evidence_for_an_article():
    tagline = "Anthropic is an AI safety and research company that's working to build reliable, interpretable, and steerable AI systems."
    item = _item("boilerplate", "anthropic_blog", 9, "Anthropic",
                 title="Investigating unintended model actions in our evaluations and internal use",
                 summary=tagline, original_content=tagline)
    assert build_signal_feed([item], {"boilerplate": _quick_read()})["total"] == 0


def test_signal_feed_filters_pr_and_duplicates_but_keeps_original_content():
    items = [
        _item("pr", "blog", 8, "Google AI Blog", content_bucket="corporate"),
        _item("launch", "blog", 10, "Google DeepMind Blog", content_bucket="product_launch",
              summary="Google released a new AI model with a documented API and examples that developers can test today."),
        _item("duplicate", "blog", 10, "Google AI Blog", content_bucket="product_launch", dup_of="launch"),
        _item("paper", "paper", 8,
              original_content="This paper proposes a reproducible evaluation method for agents with annotated failure cases and baseline results."),
        _item("x", "x", 8,
              summary="A builder published an AI agent use case with implementation notes, benchmarks, and a working public demo for others to test.",
              metadata={"engagement": "54 likes", "volume": 54, "author": "builder"}),
    ]
    saved = len(items)
    feed = build_signal_feed(items, {
        "launch": _quick_read(), "paper": _quick_read(insight="可用于评估 agent 的新方法和基线结果。"),
        "x": _quick_read(),
    }, limit=3)
    assert feed["total"] == 3
    assert set(i["id"] for i in feed["inspiration"] + feed["execution"]) == {"launch", "paper", "x"}
    assert feed["execution"][0]["so_what"] == "可用于评估 agent 的新方法和基线结果。"
    assert any("54 likes" in i["why"] for i in feed["inspiration"])
    assert len(items) == saved


def test_generic_rss_does_not_crowd_out_ai_builder_signals():
    items = [
        _item("bookshelves", "rss", 9, "Design Blog", summary="My favorite design bookshelves"),
        _item("agent-tools", "rss", 8, "Builder Blog",
              summary="Agent tools and LLM workflows for developers with a working demo and implementation details."),
        _item("hn-digest", "hackernews", 9, "HackerNews Daily", summary="Top stories roundup"),
    ]
    feed = build_signal_feed(items, {"agent-tools": _quick_read()})
    assert [i["id"] for i in feed["inspiration"]] == ["agent-tools"]


def test_signal_feed_has_global_15_item_limit_and_source_diversity():
    items = [_item(f"n{i}", "rss", 9, "One Newsletter",
                   summary="New LLM agent workflow with an open implementation, concrete results and instructions for reproduction.") for i in range(30)]
    items += [_item(f"x{i}", "x", 8, "X",
                    summary="A developer published an AI agent workflow with source code, concrete results and instructions for others to reproduce it.",
                    metadata={"author": f"author{i}", "volume": 42, "engagement": "42 likes"}) for i in range(7)]
    items += [_item(f"p{i}", "paper", 8, f"Paper {i}",
                    original_content="An abstract describing a new agent method and its evaluation on multiple datasets with benchmarks.") for i in range(7)]
    feed = build_signal_feed(items, {i["id"]: _quick_read() for i in items}, limit=15)
    ids = [i["id"] for i in feed["inspiration"] + feed["execution"]]
    assert len(ids) == feed["total"] == 15
    assert sum(i.startswith("n") for i in ids) <= 2
    assert len(feed["inspiration"]) >= 5
    assert len(feed["execution"]) >= 5


def test_daily_signal_does_not_resurface_old_rss_entries(monkeypatch):
    day = "2026-10-10"
    items = [
        _item("stale", "rss", 10, "AI Blog", published_at="2026-09-01",
              original_content="AI agent research news with an implementation, reproducible benchmarks and published results."),
        _item("paper", "paper", 8,
              original_content="A new paper proposes an agent evaluation method with benchmarks and concrete research findings."),
    ]
    monkeypatch.setattr(briefing_generator, "_load_content_file", lambda date: items if date == day else [])
    monkeypatch.setattr(briefing_generator, "get_all_dates", lambda: [day])
    monkeypatch.setattr(briefing_generator, "save_briefing_file", lambda data: None)
    monkeypatch.setattr(briefing_generator, "load_quick_reads", lambda date: {
        item["id"]: _quick_read() for item in items
    })
    briefing = briefing_generator.generate_briefing_for_date(day)
    assert [item["id"] for item in briefing["signals"]["inspiration"]] == []
    assert [item["id"] for item in briefing["signals"]["execution"]] == ["paper"]


def test_briefing_exposes_signal_feed_without_losing_full_items(monkeypatch):
    items = [
        _item("paper", "paper", 8,
              original_content="A paper describing a reproducible agent workflow with measured benchmark results and limitations."),
        _item("x", "x", 9,
              summary="A builder shared an AI product concept with sample code, benchmarks and concrete results for other teams to review.",
              metadata={"author": "builder", "volume": 42, "engagement": "42 likes"}),
    ]
    monkeypatch.setattr(briefing_generator, "_load_content_file", lambda date: items)
    monkeypatch.setattr(briefing_generator, "get_all_dates", lambda: ["2026-10-10"])
    monkeypatch.setattr(briefing_generator, "save_briefing_file", lambda data: None)
    monkeypatch.setattr(briefing_generator, "load_quick_reads", lambda date: {
        "paper": _quick_read(), "x": _quick_read(),
    }, raising=False)
    briefing = briefing_generator.generate_briefing_for_date("2026-10-10")
    assert len(briefing["items"]) == 2
    assert briefing["signals"]["total"] == 2
    assert briefing["signals"]["inspiration"][0]["id"] == "x"


# ── 学习驱动的筛选与去重（可控样本） ──

from backend.services import signal_learning as _learning


def _reference_with(pref_id, topic, evidence_forms, query):
    return {
        "id": pref_id, "url": f"https://example.com/{pref_id}", "title": f"参考 {pref_id}",
        "user_reason": "", "user_wants": "", "content_snippet": topic, "status": "active",
        "analysis_status": "complete",
        "analysis": {
            "topic": topic, "scenario": "", "contribution_type": "experience",
            "contribution": topic, "value_reason": "", "value_reason_source": "inferred",
            "evidence_forms": evidence_forms,
            "search_clues": [{"query": query, "subreddits": [], "handles": []}],
            "uncertain": "",
        },
        "feedback": [],
    }


def test_useful_content_outside_initial_five_tags_is_selected():
    # 不含五类标签关键词、但确有具体认识的内容仍可入选（标签不是门槛）。
    item = _item("unlabeled", "blog", 9, "AI Company", content_bucket="technical",
                 summary="An AI model latent-space compression trick reduces memory use with reproducible numbers.",
                 original_content="The compression approach for the AI model reduces memory and includes measured results.")
    feed = build_signal_feed([item], {"unlabeled": _quick_read(
        core="提出一种模型隐空间压缩方式，实测内存占用下降。",
        insight="可以在自己的推理服务里尝试同样压缩思路，评估收益。")})
    assert feed["total"] == 1
    assert feed["execution"][0]["tags"] == []


def test_short_important_announcement_not_filtered_by_length():
    # 简短的重要公告：长度不是硬门槛，有互动证据和成文速读即可入选。
    post = "We now support function calling."
    item = _item("short", "x", 9, title=post, summary=post,
                 metadata={"author": "builder", "engagement": "31 likes, 4 replies", "volume": 35})
    feed = build_signal_feed([item], {"short": _quick_read(
        core="该服务新增 function calling 支持，可接入结构化工具调用。",
        insight="此前缺的接口现在补齐，可以评估迁移。")})
    assert [i["id"] for i in feed["inspiration"]] == ["short"]


def test_quote_with_missing_context_notes_boundary_not_fabricated():
    post = "Important: the referenced post claims a new capability."
    item = _item("quote", "x", 9, title=post, summary=post,
                 metadata={"author": "builder", "engagement": "22 likes", "volume": 22,
                           "post_type": "quote", "quoted_url": "https://x.com/other/status/1"})
    feed = build_signal_feed([item], {"quote": _quick_read(
        core="作者引用了一篇声称具备新能力的第三方帖子。",
        insight="需要先核对被引用原文是否属实，再决定是否采信。")})
    card = feed["inspiration"][0]
    assert "引用" in card["evidence_note"] and "未随文核验" in card["evidence_note"]
    assert card["quoted_url"] == "https://x.com/other/status/1"


def test_same_source_different_events_are_not_merged():
    items = [
        _item("launch-a", "blog", 9, "AI Company", content_bucket="technical",
              summary="Company released an inference runtime with public benchmarks."),
        _item("launch-b", "blog", 8, "AI Company", content_bucket="technical",
              summary="Company released a different AI model evaluation dataset tool with public benchmarks."),
    ]
    feed = build_signal_feed(items, {i["id"]: _quick_read() for i in items})
    ids = [i["id"] for i in feed["execution"]]
    assert set(ids) == {"launch-a", "launch-b"}


def test_same_topic_independent_practices_are_not_deduped():
    items = [
        _item("practice-1", "reddit", 8, title="How I run agent evals",
              summary="A team's full evaluation workflow with failure cases and costs.",
              metadata={"author": "a", "volume": 40, "engagement": "40 upvotes, 5 replies"}),
        _item("practice-2", "reddit", 8, title="A different agent eval setup",
              summary="An opposing take with a different workflow and counterexample results.",
              metadata={"author": "b", "volume": 40, "engagement": "40 upvotes, 5 replies"}),
    ]
    feed = build_signal_feed(items, {i["id"]: _quick_read() for i in items})
    assert {i["id"] for i in feed["inspiration"]} == {"practice-1", "practice-2"}


def test_learned_value_match_reorders_and_marks_card():
    preferences = _learning.build_preferences([
        _reference_with("r1", "Agent 处理客服记录", ["process", "failure", "cost"], "agent 客服 流程")
    ])
    items = [
        _item("generic", "rss", 9, "Newsletter",
              summary="New LLM agent workflow with open implementation and results."),
        _item("valued", "rss", 7, "Builder Blog",
              summary="We processed support tickets with an agent: full pipeline, failure cases, and cost."),
    ]
    feed = build_signal_feed(items, {i["id"]: _quick_read() for i in items}, limit=5,
                             preferences=preferences)
    ids = [i["id"] for i in feed["inspiration"] + feed["execution"]]
    assert ids == ["valued", "generic"] or ids[0] == "valued"
    valued = next(i for i in feed["inspiration"] + feed["execution"] if i["id"] == "valued")
    assert "r1" in valued.get("learned_from", [])


def test_learned_value_match_relaxes_x_engagement_but_topic_only_does_not():
    preferences = _learning.build_preferences([
        _reference_with("r1", "Agent 处理客服记录", ["process", "failure"], "agent 客服 流程")
    ])
    # 低互动但命中价值特征：放宽到 5 次互动以上即可入选。
    valued = _item("valued", "x", 8,
                   title="We processed tickets with an agent, full pipeline and failures.",
                   summary="We processed tickets with an agent, full pipeline and failures.",
                   metadata={"author": "a", "engagement": "6 likes", "volume": 6})
    # 低互动且只命中品牌词（主题）不命中价值特征：仍被过滤。
    topic_only = _item("topic-only", "x", 8,
                       title="Agent for customer service is promising.",
                       summary="Agent for customer service is promising.",
                       metadata={"author": "b", "engagement": "6 likes", "volume": 6})
    feed = build_signal_feed([valued, topic_only], {i["id"]: _quick_read() for i in [valued, topic_only]},
                             preferences=preferences)
    ids = [i["id"] for i in feed["inspiration"]]
    assert "valued" in ids
    assert "topic-only" not in ids
