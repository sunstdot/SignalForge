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
