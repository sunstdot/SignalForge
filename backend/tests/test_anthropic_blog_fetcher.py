from datetime import date

import pytest

from backend.services import anthropic_blog_fetcher as fetcher

ENGINEERING_HTML = """
<article><a href="/engineering/technical-agents"><h3>Building effective agents</h3>
<time dateTime="2026-10-09">Oct 9, 2026</time></a></article>
<article><a href="/engineering/old"><h3>Older technical article</h3>
<time dateTime="2026-09-01">Sep 1, 2026</time></a></article>
<article><a href="/news/press"><h3>Company announcement</h3>
<time dateTime="2026-10-09">Oct 9, 2026</time></a></article>
"""
RESEARCH_HTML = """
<a href="/research/team/alignment">Alignment</a>
<li><a class="PublicationList-module__listItem" href="/research/technical-evals">
  <div><time>Oct 8, 2026</time><span>Alignment</span></div>
  <span class="PublicationList-module__title">Investigating unintended model actions</span>
</a></li>
<li><a href="/research/old-paper"><time>Sep 1, 2026</time>
  <span class="PublicationList-module__title">Old research</span></a></li>
"""
DETAIL_HTML = '<html><head><meta name="description" content="How to evaluate tools"></head><body><main><article><p>Methods and results of evaluating agent tools.</p></article></main></body></html>'


def test_parse_engineering_and_research_page_formats():
    engineering = fetcher.parse_anthropic_articles(ENGINEERING_HTML, "engineering")
    research = fetcher.parse_anthropic_articles(RESEARCH_HTML, "research")
    assert [(a["title"], a["published_at"], a["section"]) for a in engineering] == [
        ("Building effective agents", "2026-10-09", "engineering"),
        ("Older technical article", "2026-09-01", "engineering"),
    ]
    assert [(a["title"], a["published_at"], a["section"]) for a in research] == [
        ("Investigating unintended model actions", "2026-10-08", "research"),
        ("Old research", "2026-09-01", "research"),
    ]
    assert all(a["url"].startswith("https://www.anthropic.com/") for a in engineering + research)


@pytest.mark.asyncio
async def test_fetch_only_recent_verified_articles_with_content(monkeypatch):
    async def fake_fetch(url):
        if url.endswith("/engineering"):
            return ENGINEERING_HTML
        if url.endswith("/research"):
            return RESEARCH_HTML
        return DETAIL_HTML

    monkeypatch.setattr(fetcher, "_fetch_html", fake_fetch, raising=False)
    items = await fetcher.fetch_anthropic_technical_articles("2026-10-10")
    assert [i["title"] for i in items] == [
        "Building effective agents", "Investigating unintended model actions"
    ]
    assert [i["published_at"] for i in items] == ["2026-10-09", "2026-10-08"]
    assert all(i["source_type"] == "anthropic_blog" for i in items)
    assert all("Methods and results" in i["raw_text"] for i in items)
    assert all(i["created_at"] == "2026-10-10" for i in items)


@pytest.mark.asyncio
async def test_fetch_survives_one_section_failure_without_fabricating_entries(monkeypatch):
    async def fake_fetch(url):
        if url.endswith("/research"):
            raise RuntimeError("blocked")
        return ENGINEERING_HTML if url.endswith("/engineering") else DETAIL_HTML

    monkeypatch.setattr(fetcher, "_fetch_html", fake_fetch, raising=False)
    items = await fetcher.fetch_anthropic_technical_articles("2026-10-10")
    assert [i["title"] for i in items] == ["Building effective agents"]


def test_normalize_url_drops_tracking_query():
    assert fetcher.normalize_url("https://www.anthropic.com/engineering/a/?utm_source=x") == (
        "https://www.anthropic.com/engineering/a"
    )
