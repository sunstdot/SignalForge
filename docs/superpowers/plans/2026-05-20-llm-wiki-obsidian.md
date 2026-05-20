# LLM Wiki + Obsidian Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an LLM-powered Wiki engine that processes manually entered articles, extracts concepts, discovers cross-article connections, and writes structured Markdown notes into an Obsidian Vault.

**Architecture:** Three-step pipeline per article — (1) LLM extracts concepts from `content_snippet`, (2) concept-overlap finds candidate articles (no LLM), (3) LLM compares full `content_snippet`s for deep connection analysis. Results are persisted to `data/wiki/` and written as Obsidian `.md` files. Triggered automatically after `quick_read` completes for new manual intel items.

**Tech Stack:** FastAPI, Python asyncio, existing `chat_async` from `services/llm_client.py`, file-based JSON storage, Obsidian Vault (local filesystem writes).

**Scope:** Only processes `data/manual_intel/` items. Auto-crawled content is excluded.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/services/storage.py` | Modify (append) | Wiki CRUD: concepts, article_nodes |
| `backend/services/wiki_builder.py` | Create | Core pipeline: extract → connect → write Obsidian files |
| `backend/routers/wiki.py` | Create | API: sync, rebuild, status, concepts, delete-concept |
| `backend/routers/manual_intel.py` | Modify | Trigger wiki after `quick_read` completes |
| `backend/main.py` | Modify | Register wiki router |
| `.env.example` | Modify | Document OBSIDIAN_VAULT_PATH, WIKI_SYNTHESIS_THRESHOLD |
| `backend/tests/test_wiki_storage.py` | Create | Storage layer tests |
| `backend/tests/test_wiki_builder.py` | Create | Wiki builder unit tests with mocked LLM |
| `backend/tests/test_wiki_router.py` | Create | Router endpoint tests |

---

## Task 1: Storage Layer — Wiki CRUD Functions

**Files:**
- Modify: `backend/services/storage.py` (append to end of file)
- Create: `backend/tests/test_wiki_storage.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_wiki_storage.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def isolated_wiki(monkeypatch, tmp_path):
    import services.storage as s
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr(s, "WIKI_DIR", wiki_dir)
    yield wiki_dir


def test_upsert_and_get_concept():
    from services.storage import upsert_wiki_concept, get_wiki_concepts

    c = upsert_wiki_concept("In-Context Learning", "in-context-learning", "A definition", "item-1")
    assert c["name"] == "In-Context Learning"
    assert c["slug"] == "in-context-learning"
    assert "item-1" in c["article_ids"]

    all_concepts = get_wiki_concepts()
    assert len(all_concepts) == 1


def test_upsert_concept_accumulates_article_ids():
    from services.storage import upsert_wiki_concept

    upsert_wiki_concept("RAG", "rag", "Retrieval Augmented Generation", "item-1")
    upsert_wiki_concept("RAG", "rag", "Retrieval Augmented Generation", "item-2")
    upsert_wiki_concept("RAG", "rag", "Retrieval Augmented Generation", "item-1")  # duplicate

    from services.storage import get_wiki_concepts
    concepts = get_wiki_concepts()
    assert len(concepts) == 1
    assert sorted(concepts[0]["article_ids"]) == ["item-1", "item-2"]


def test_delete_concept():
    from services.storage import upsert_wiki_concept, delete_wiki_concept, get_wiki_concepts

    upsert_wiki_concept("RAG", "rag", "def", "item-1")
    ok = delete_wiki_concept("rag")
    assert ok is True
    assert get_wiki_concepts() == []


def test_delete_nonexistent_concept():
    from services.storage import delete_wiki_concept
    assert delete_wiki_concept("does-not-exist") is False


def test_upsert_and_get_article_node():
    from services.storage import upsert_wiki_article_node, get_wiki_article_node, get_wiki_article_nodes

    node = upsert_wiki_article_node(
        item_id="item-1",
        slug="my-article",
        concepts=["RAG", "LLM"],
        related_articles=[{"item_id": "item-2", "title": "Other", "reason": "both cover RAG"}],
    )
    assert node["item_id"] == "item-1"
    assert node["slug"] == "my-article"
    assert "wiki_synced_at" in node

    fetched = get_wiki_article_node("item-1")
    assert fetched is not None
    assert fetched["concepts"] == ["RAG", "LLM"]

    all_nodes = get_wiki_article_nodes()
    assert len(all_nodes) == 1


def test_upsert_article_node_updates_existing():
    from services.storage import upsert_wiki_article_node, get_wiki_article_node

    upsert_wiki_article_node("item-1", "slug-v1", ["RAG"], [])
    upsert_wiki_article_node("item-1", "slug-v2", ["RAG", "LLM"], [])

    node = get_wiki_article_node("item-1")
    assert node["slug"] == "slug-v2"
    assert node["concepts"] == ["RAG", "LLM"]

    from services.storage import get_wiki_article_nodes
    assert len(get_wiki_article_nodes()) == 1


def test_get_wiki_article_node_missing():
    from services.storage import get_wiki_article_node
    assert get_wiki_article_node("nonexistent") is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
source venv/bin/activate
cd backend
python -m pytest tests/test_wiki_storage.py -v
```

Expected: `ImportError` — functions not yet defined.

- [ ] **Step 3: Implement storage functions**

Append to the end of `backend/services/storage.py`:

```python
# ───────────────────────── Wiki ─────────────────────────

WIKI_DIR = DATA_DIR / "wiki"
WIKI_DIR.mkdir(parents=True, exist_ok=True)


def _load_wiki_concepts() -> List[Dict]:
    f = WIKI_DIR / "concepts.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def _save_wiki_concepts(concepts: List[Dict]):
    (WIKI_DIR / "concepts.json").write_text(
        json.dumps(concepts, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _load_wiki_article_nodes() -> List[Dict]:
    f = WIKI_DIR / "article_nodes.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def _save_wiki_article_nodes(nodes: List[Dict]):
    (WIKI_DIR / "article_nodes.json").write_text(
        json.dumps(nodes, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def get_wiki_concepts() -> List[Dict]:
    return _load_wiki_concepts()


def get_wiki_article_nodes() -> List[Dict]:
    return _load_wiki_article_nodes()


def get_wiki_article_node(item_id: str) -> Optional[Dict]:
    for node in _load_wiki_article_nodes():
        if node["item_id"] == item_id:
            return node
    return None


def upsert_wiki_concept(name: str, slug: str, description: str, article_id: str) -> Dict:
    concepts = _load_wiki_concepts()
    now = datetime.now().isoformat()
    for c in concepts:
        if c["slug"] == slug:
            if article_id not in c["article_ids"]:
                c["article_ids"].append(article_id)
            c["updated_at"] = now
            _save_wiki_concepts(concepts)
            return c
    new_concept = {
        "name": name,
        "slug": slug,
        "description": description,
        "article_ids": [article_id],
        "created_at": now,
        "updated_at": now,
    }
    concepts.append(new_concept)
    _save_wiki_concepts(concepts)
    return new_concept


def delete_wiki_concept(slug: str) -> bool:
    concepts = _load_wiki_concepts()
    new_concepts = [c for c in concepts if c["slug"] != slug]
    if len(new_concepts) == len(concepts):
        return False
    _save_wiki_concepts(new_concepts)
    return True


def upsert_wiki_article_node(
    item_id: str, slug: str, concepts: List[str], related_articles: List[Dict]
) -> Dict:
    nodes = _load_wiki_article_nodes()
    now = datetime.now().isoformat()
    for node in nodes:
        if node["item_id"] == item_id:
            node.update({
                "slug": slug,
                "concepts": concepts,
                "related_articles": related_articles,
                "wiki_synced_at": now,
            })
            _save_wiki_article_nodes(nodes)
            return node
    new_node = {
        "item_id": item_id,
        "slug": slug,
        "concepts": concepts,
        "related_articles": related_articles,
        "wiki_synced_at": now,
    }
    nodes.append(new_node)
    _save_wiki_article_nodes(nodes)
    return new_node
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_wiki_storage.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
git add backend/services/storage.py backend/tests/test_wiki_storage.py
git commit -m "feat: add wiki storage layer (concepts + article_nodes CRUD)"
```

---

## Task 2: Wiki Builder Service

**Files:**
- Create: `backend/services/wiki_builder.py`
- Create: `backend/tests/test_wiki_builder.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_wiki_builder.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def isolated_wiki(monkeypatch, tmp_path):
    import services.storage as s
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr(s, "WIKI_DIR", wiki_dir)
    yield wiki_dir


@pytest.fixture
def vault_path(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


# ── _slugify ────────────────────────────────────────────────────────────────

def test_slugify_basic():
    from services.wiki_builder import _slugify
    assert _slugify("In-Context Learning") == "in-context-learning"


def test_slugify_special_chars():
    from services.wiki_builder import _slugify
    assert _slugify("RAG: Retrieval & Search!") == "rag-retrieval-search"


def test_slugify_long_string():
    from services.wiki_builder import _slugify
    result = _slugify("a" * 100)
    assert len(result) <= 60


# ── _extract_concepts ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_concepts_returns_list():
    from services.wiki_builder import _extract_concepts

    mock_response = '[{"name": "RAG", "description": "Retrieval Augmented Generation"}]'
    with patch("services.wiki_builder.chat_async", new=AsyncMock(return_value=mock_response)):
        result = await _extract_concepts("Test Title", "Some content")
    assert isinstance(result, list)
    assert result[0]["name"] == "RAG"


@pytest.mark.asyncio
async def test_extract_concepts_handles_llm_failure():
    from services.wiki_builder import _extract_concepts

    with patch("services.wiki_builder.chat_async", new=AsyncMock(side_effect=Exception("LLM error"))):
        result = await _extract_concepts("Title", "Content")
    assert result == []


@pytest.mark.asyncio
async def test_extract_concepts_handles_bad_json():
    from services.wiki_builder import _extract_concepts

    with patch("services.wiki_builder.chat_async", new=AsyncMock(return_value="not json at all")):
        result = await _extract_concepts("Title", "Content")
    assert result == []


# ── _find_candidate_articles ─────────────────────────────────────────────────

def test_find_candidates_by_shared_concept(monkeypatch):
    from services.wiki_builder import _find_candidate_articles
    import services.storage as s

    s.upsert_wiki_article_node("item-A", "article-a", ["RAG", "LLM"], [])
    s.upsert_wiki_article_node("item-B", "article-b", ["Vector Search"], [])

    fake_item_a = {"id": "item-A", "title": "Article A", "content_snippet": "content A"}
    monkeypatch.setattr(s, "get_manual_intel_item_by_id",
                        lambda iid: fake_item_a if iid == "item-A" else None)

    new_concepts = [{"name": "RAG", "description": "def"}]
    candidates = _find_candidate_articles(new_concepts, "item-NEW")
    assert len(candidates) == 1
    assert candidates[0]["id"] == "item-A"


def test_find_candidates_excludes_self(monkeypatch):
    from services.wiki_builder import _find_candidate_articles
    import services.storage as s

    s.upsert_wiki_article_node("item-A", "article-a", ["RAG"], [])

    new_concepts = [{"name": "RAG", "description": "def"}]
    candidates = _find_candidate_articles(new_concepts, "item-A")
    assert candidates == []


# ── _analyze_connections ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_connections_no_candidates():
    from services.wiki_builder import _analyze_connections
    result = await _analyze_connections({"title": "T", "content_snippet": "c"}, [])
    assert result == {"related_articles": [], "additional_insights": ""}


@pytest.mark.asyncio
async def test_analyze_connections_returns_related():
    from services.wiki_builder import _analyze_connections

    mock_response = '{"related_articles": [{"title": "Other Article", "reason": "Both cover RAG"}], "additional_insights": ""}'
    with patch("services.wiki_builder.chat_async", new=AsyncMock(return_value=mock_response)):
        result = await _analyze_connections(
            {"title": "New", "content_snippet": "new content"},
            [{"title": "Other Article", "content_snippet": "other content"}],
        )
    assert len(result["related_articles"]) == 1
    assert result["related_articles"][0]["reason"] == "Both cover RAG"


# ── _write_article_note ──────────────────────────────────────────────────────

def test_write_article_note_creates_file(vault_path):
    from services.wiki_builder import _write_article_note

    item = {
        "title": "Test Article",
        "url": "https://example.com",
        "source_platform": "Blog",
        "added_at": "2026-05-20T10:00:00",
        "quick_read": "**核心内容**: test",
        "user_note": "great read",
    }
    concepts = [{"name": "RAG", "description": "def"}]
    _write_article_note(vault_path, item, concepts, [], "test-article")

    note_path = vault_path / "articles" / "test-article.md"
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "Test Article" in content
    assert "[[RAG]]" in content
    assert "great read" in content


def test_write_article_note_with_related(vault_path):
    from services.wiki_builder import _write_article_note

    item = {
        "title": "T", "url": "https://x.com", "source_platform": "Blog",
        "added_at": "2026-05-20", "quick_read": "summary", "user_note": "",
    }
    related = [{"item_id": "id-2", "title": "Other Article", "reason": "shared theme"}]
    _write_article_note(vault_path, item, [], related, "t-slug")

    content = (vault_path / "articles" / "t-slug.md").read_text()
    assert "[[other-article]]" in content
    assert "shared theme" in content


# ── _write_concept_note ──────────────────────────────────────────────────────

def test_write_concept_note_creates_file(vault_path):
    from services.wiki_builder import _write_concept_note

    concept = {"name": "RAG", "slug": "rag", "description": "Retrieval Augmented Generation"}
    _write_concept_note(vault_path, concept, ["article-one", "article-two"])

    note_path = vault_path / "concepts" / "rag.md"
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "article_count: 2" in content
    assert "[[article-one]]" in content


# ── process_article (integration) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_article_full_pipeline(monkeypatch, vault_path):
    import services.storage as s
    from services.wiki_builder import process_article

    item = {
        "id": "item-1",
        "title": "Learning Beyond Gradients",
        "url": "https://example.com/article",
        "source_platform": "Blog",
        "added_at": "2026-05-20T10:00:00",
        "quick_read": "**核心内容**: about learning without gradients",
        "user_note": "",
        "content_snippet": "This article discusses in-context learning and meta-learning approaches.",
        "business_opps": [],
        "rdev_opps": [],
    }
    monkeypatch.setattr(s, "get_manual_intel_item_by_id", lambda iid: item if iid == "item-1" else None)
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault_path))
    monkeypatch.setenv("WIKI_SYNTHESIS_THRESHOLD", "3")

    concepts_response = '[{"name": "In-Context Learning", "description": "Learning from examples in prompt"}]'
    connections_response = '{"related_articles": [], "additional_insights": ""}'

    call_count = 0

    async def mock_chat(messages, provider=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return concepts_response
        return connections_response

    monkeypatch.setattr("services.wiki_builder.chat_async", mock_chat)

    await process_article("item-1")

    # Article note written
    assert (vault_path / "articles" / "learning-beyond-gradients.md").exists()
    # Concept note written
    assert (vault_path / "concepts" / "in-context-learning.md").exists()
    # Index updated
    assert (vault_path / "_index.md").exists()
    # Data persisted
    node = s.get_wiki_article_node("item-1")
    assert node is not None
    assert "In-Context Learning" in node["concepts"]


@pytest.mark.asyncio
async def test_process_article_skips_if_no_quick_read(monkeypatch):
    import services.storage as s
    from services.wiki_builder import process_article

    item = {"id": "item-1", "title": "T", "quick_read": "", "content_snippet": "c"}
    monkeypatch.setattr(s, "get_manual_intel_item_by_id", lambda iid: item)

    called = []
    async def mock_chat(messages, provider=None):
        called.append(True)
        return "[]"

    monkeypatch.setattr("services.wiki_builder.chat_async", mock_chat)
    await process_article("item-1")
    assert called == []  # LLM not called when quick_read is empty
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_wiki_builder.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'services.wiki_builder'`

- [ ] **Step 3: Create `backend/services/wiki_builder.py`**

```python
"""LLM Wiki Builder — processes manual intel articles into Obsidian notes."""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from services.llm_client import chat_async
from services.storage import (
    get_manual_intel_item_by_id,
    get_wiki_concepts,
    get_wiki_article_nodes,
    get_wiki_article_node,
    upsert_wiki_concept,
    upsert_wiki_article_node,
)


def _get_vault_path() -> Optional[Path]:
    vault = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    if not vault:
        print("[wiki] OBSIDIAN_VAULT_PATH not set, skipping Obsidian file writing")
        return None
    return Path(vault)


def _get_synthesis_threshold() -> int:
    try:
        return int(os.environ.get("WIKI_SYNTHESIS_THRESHOLD", "3"))
    except ValueError:
        return 3


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:60]


async def _extract_concepts(title: str, content_snippet: str) -> list:
    prompt = f"""从以下文章中提取 5-10 个核心知识概念或技术实体。
概念要求：
- 用英文或中文，保持专业术语一致性（如 "RAG" 不要写成 "检索增强生成"）
- 粒度适中，不要太宽泛（"AI" 不是概念），不要太具体（"GPT-4o 的温度参数" 不是概念）
- 每个概念附一句话定义

文章标题：{title}
文章内容：{content_snippet}

输出严格 JSON，不要 markdown 代码块：
[{{"name": "...", "description": "..."}}]"""

    try:
        raw = (await chat_async([{"role": "user", "content": prompt}], provider="deepseek")).strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        result = json.loads(match.group(0) if match else raw)
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"[wiki] concept extraction failed: {e}")
        return []


def _find_candidate_articles(new_concepts: list, new_item_id: str) -> list:
    """Find existing articles sharing at least one concept with the new article. No LLM."""
    nodes = get_wiki_article_nodes()
    new_concept_names = {c["name"] for c in new_concepts}
    candidate_ids = {
        node["item_id"]
        for node in nodes
        if node["item_id"] != new_item_id
        and set(node.get("concepts", [])) & new_concept_names
    }
    return [item for iid in candidate_ids if (item := get_manual_intel_item_by_id(iid))]


async def _analyze_connections(new_item: dict, candidates: list) -> dict:
    if not candidates:
        return {"related_articles": [], "additional_insights": ""}

    candidates_text = "\n\n".join(
        f"[{c['title']}]\n{c.get('content_snippet', '')[:3000]}" for c in candidates
    )
    prompt = f"""你是一个知识图谱构建助手。

新文章：{new_item['title']}
新文章内容：{new_item.get('content_snippet', '')[:3000]}

候选关联文章：
{candidates_text}

任务：
1. 从候选文章中找出与新文章有实质关联的文章（可以是 0 篇），说明关联原因（超越共享概念的深层主题联系）
2. 识别跨文章发现的额外洞察

输出严格 JSON，不要 markdown 代码块：
{{
  "related_articles": [{{"title": "...", "reason": "..."}}],
  "additional_insights": "..."
}}"""

    try:
        raw = (await chat_async([{"role": "user", "content": prompt}], provider="deepseek")).strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group(0) if match else raw)
        return result if isinstance(result, dict) else {"related_articles": [], "additional_insights": ""}
    except Exception as e:
        print(f"[wiki] connection analysis failed: {e}")
        return {"related_articles": [], "additional_insights": ""}


def _write_article_note(
    vault_path: Path, item: dict, concepts: list, related_articles: list, slug: str
):
    articles_dir = vault_path / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    concept_links = "\n".join(f"- [[{c['name']}]] — {c['description']}" for c in concepts)
    related_links = "\n".join(
        f"- [[{_slugify(r['title'])}]] — {r['reason']}" for r in related_articles
    )
    related_section = f"\n## 关联文章\n{related_links}" if related_articles else ""
    user_note = item.get("user_note", "")
    note_section = f"\n## 我的点评\n{user_note}" if user_note else ""
    concept_names = ", ".join(c["name"] for c in concepts)

    content = f"""---
title: {item['title']}
url: {item['url']}
platform: {item.get('source_platform', 'other')}
added: {item.get('added_at', '')[:10]}
concepts: [{concept_names}]
---

## 速读摘要
{item.get('quick_read', '（待生成）')}
{note_section}
## 知识关联
{concept_links or '（无）'}
{related_section}
""".strip()

    (articles_dir / f"{slug}.md").write_text(content, encoding="utf-8")


def _write_concept_note(vault_path: Path, concept: dict, article_slugs: list):
    concepts_dir = vault_path / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    article_links = "\n".join(f"- [[{s}]]" for s in article_slugs)
    content = f"""---
type: concept
article_count: {len(article_slugs)}
updated: {datetime.now().strftime('%Y-%m-%d')}
---

## 定义
{concept['description']}

## 引用此概念的文章
{article_links or '（无）'}
""".strip()

    (concepts_dir / f"{concept['slug']}.md").write_text(content, encoding="utf-8")


async def _maybe_generate_synthesis(vault_path: Path, concept: dict, threshold: int):
    article_ids = concept.get("article_ids", [])
    if len(article_ids) < threshold:
        return

    articles = [a for aid in article_ids if (a := get_manual_intel_item_by_id(aid))]
    articles_text = "\n\n".join(
        f"[{a['title']}]\n{a.get('content_snippet', '')[:2000]}" for a in articles
    )
    prompt = f"""以下 {len(articles)} 篇文章都涉及概念「{concept['name']}」：

{articles_text}

请综合这些文章，生成一篇「{concept['name']}」的知识合成笔记，包含：
1. 核心定义与当前认知边界
2. 这些文章呈现了哪些不同视角或争议
3. 跨文章发现的隐含规律（在任何单篇文章中都没有显式出现的结论）
4. 值得继续关注的开放问题

用中文输出，Markdown 格式，不要输出 frontmatter。"""

    try:
        body = (await chat_async([{"role": "user", "content": prompt}])).strip()
    except Exception as e:
        print(f"[wiki] synthesis failed for {concept['name']}: {e}")
        return

    synthesis_dir = vault_path / "synthesis"
    synthesis_dir.mkdir(parents=True, exist_ok=True)

    article_refs = "\n".join(f"- [[{_slugify(a['title'])}]]" for a in articles)
    full_content = f"""---
type: synthesis
concept: {concept['name']}
article_count: {len(articles)}
generated: {datetime.now().strftime('%Y-%m-%d')}
---

## 来源文章
{article_refs}

{body}
""".strip()

    (synthesis_dir / f"{concept['slug']}-synthesis.md").write_text(full_content, encoding="utf-8")


def _update_index(vault_path: Path):
    nodes = get_wiki_article_nodes()
    concepts = get_wiki_concepts()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    article_lines = "\n".join(f"- [[articles/{n['slug']}]]" for n in nodes)
    concept_lines = "\n".join(
        f"- [[concepts/{c['slug']}|{c['name']}]] ({len(c['article_ids'])} 篇)"
        for c in sorted(concepts, key=lambda x: len(x["article_ids"]), reverse=True)
    )
    synthesis_dir = vault_path / "synthesis"
    synthesis_files = list(synthesis_dir.glob("*.md")) if synthesis_dir.exists() else []
    synthesis_lines = "\n".join(f"- [[synthesis/{f.stem}]]" for f in synthesis_files)

    content = f"""# SignalForge Wiki — Map of Content

> 自动生成，最后更新：{now}

## 文章收藏（{len(nodes)} 篇）
{article_lines or '（暂无）'}

## 知识概念（{len(concepts)} 个）
{concept_lines or '（暂无）'}

## 合成洞察
{synthesis_lines or '（暂无，概念积累到阈值后自动生成）'}
""".strip()

    (vault_path / "_index.md").write_text(content, encoding="utf-8")


async def process_article(item_id: str):
    """Main entry point: process one manual intel article into the Wiki."""
    item = get_manual_intel_item_by_id(item_id)
    if not item:
        print(f"[wiki] item {item_id} not found")
        return

    if not item.get("quick_read"):
        print(f"[wiki] item {item_id} has no quick_read yet, skipping")
        return

    vault_path = _get_vault_path()
    threshold = _get_synthesis_threshold()
    slug = _slugify(item.get("title") or item["url"])

    # Step 1: Extract concepts
    concepts = await _extract_concepts(item["title"], item.get("content_snippet", ""))
    if not concepts:
        print(f"[wiki] no concepts extracted for {item_id}")
        return

    # Step 2: Find candidate articles by concept overlap
    candidates = _find_candidate_articles(concepts, item_id)

    # Step 3: Deep connection analysis
    connection_result = await _analyze_connections(item, candidates)

    # Map titles back to item_ids for related_articles storage
    title_to_candidate = {c["title"]: c for c in candidates}
    related_articles = [
        {
            "item_id": title_to_candidate[r["title"]]["id"],
            "title": r["title"],
            "reason": r["reason"],
        }
        for r in connection_result.get("related_articles", [])
        if r["title"] in title_to_candidate
    ]

    # Persist concept nodes
    concept_names = []
    for concept in concepts:
        concept_slug = _slugify(concept["name"])
        upsert_wiki_concept(concept["name"], concept_slug, concept["description"], item_id)
        concept_names.append(concept["name"])

    # Persist article node
    upsert_wiki_article_node(item_id, slug, concept_names, related_articles)

    if not vault_path:
        return

    # Step 4a: Write article note
    _write_article_note(vault_path, item, concepts, related_articles, slug)

    # Step 4b: Update concept notes
    all_concepts = get_wiki_concepts()
    for concept in concepts:
        concept_slug = _slugify(concept["name"])
        full_concept = next((c for c in all_concepts if c["slug"] == concept_slug), None)
        if full_concept:
            article_slugs = [
                node["slug"]
                for aid in full_concept["article_ids"]
                if (node := get_wiki_article_node(aid))
            ]
            _write_concept_note(vault_path, full_concept, article_slugs)

    # Step 5: Synthesis trigger
    for concept in all_concepts:
        await _maybe_generate_synthesis(vault_path, concept, threshold)

    # Step 6: Update index
    _update_index(vault_path)

    print(
        f"[wiki] processed {item_id}: {len(concepts)} concepts, "
        f"{len(related_articles)} related articles"
    )
```

- [ ] **Step 4: Install pytest-asyncio (needed for async tests)**

```bash
pip install pytest-asyncio
```

Add to `backend/requirements.txt` if not present:
```
pytest-asyncio
```

Create or update `backend/pytest.ini` (or `pyproject.toml`) to enable asyncio mode. Check if `pytest.ini` exists:

```bash
ls /Users/shitaosun/Project/AI-Personal/SignalForge/backend/pytest.ini 2>/dev/null || echo "not found"
```

If not found, create `backend/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python -m pytest tests/test_wiki_builder.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
git add backend/services/wiki_builder.py backend/tests/test_wiki_builder.py backend/requirements.txt
git add backend/pytest.ini 2>/dev/null || true
git commit -m "feat: add wiki_builder service with concept extraction and Obsidian file writing"
```

---

## Task 3: Wiki Router + Register in main.py

**Files:**
- Create: `backend/routers/wiki.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_wiki_router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_wiki_router.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def isolated_wiki(monkeypatch, tmp_path):
    import services.storage as s
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr(s, "WIKI_DIR", wiki_dir)


@pytest.fixture(autouse=True)
def isolated_manual_intel(monkeypatch, tmp_path):
    import services.storage as s
    mi_dir = tmp_path / "manual_intel"
    mi_dir.mkdir()
    monkeypatch.setattr(s, "MANUAL_INTEL_DIR", mi_dir)


@pytest.fixture
def client():
    import importlib, sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("routers") or mod.startswith("services"):
            del sys.modules[mod]
    from main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_get_status_empty(client):
    resp = client.get("/api/wiki/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["concept_count"] == 0
    assert data["article_count"] == 0
    assert data["last_synced_at"] is None


def test_list_concepts_empty(client):
    resp = client.get("/api/wiki/concepts")
    assert resp.status_code == 200
    assert resp.json() == {"concepts": []}


def test_delete_concept_not_found(client):
    resp = client.delete("/api/wiki/concept/does-not-exist")
    assert resp.status_code == 404


def test_delete_concept_success(client):
    from services.storage import upsert_wiki_concept
    upsert_wiki_concept("RAG", "rag", "def", "item-1")

    resp = client.delete("/api/wiki/concept/rag")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp2 = client.get("/api/wiki/concepts")
    assert resp2.json() == {"concepts": []}


def test_status_reflects_data(client):
    from services.storage import upsert_wiki_concept, upsert_wiki_article_node
    upsert_wiki_concept("RAG", "rag", "def", "item-1")
    upsert_wiki_article_node("item-1", "article-1", ["RAG"], [])

    resp = client.get("/api/wiki/status")
    data = resp.json()
    assert data["concept_count"] == 1
    assert data["article_count"] == 1
    assert data["last_synced_at"] is not None


def test_sync_returns_ok(client, monkeypatch):
    import services.wiki_builder as wb
    called = []

    async def mock_process(item_id):
        called.append(item_id)

    monkeypatch.setattr(wb, "process_article", mock_process)

    resp = client.post("/api/wiki/sync/item-123")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_rebuild_returns_ok(client, monkeypatch):
    from services.storage import create_manual_intel_item
    create_manual_intel_item({"url": "https://a.com", "title": "A"})

    import services.wiki_builder as wb
    async def mock_process(item_id):
        pass
    monkeypatch.setattr(wb, "process_article", mock_process)

    resp = client.post("/api/wiki/rebuild")
    assert resp.status_code == 200
    assert "Rebuilding wiki" in resp.json()["message"]
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_wiki_router.py::test_get_status_empty -v
```

Expected: `ImportError` or 404 — router not yet registered.

- [ ] **Step 3: Create `backend/routers/wiki.py`**

```python
"""Wiki API endpoints"""
import asyncio
from fastapi import APIRouter, HTTPException
from services.storage import (
    get_wiki_concepts,
    get_wiki_article_nodes,
    delete_wiki_concept,
    get_manual_intel_items,
)
import services.wiki_builder as wiki_builder

router = APIRouter()
_background_tasks: set = set()


@router.post("/sync/{item_id}")
async def sync_article(item_id: str):
    task = asyncio.create_task(wiki_builder.process_article(item_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"ok": True, "message": f"Wiki sync started for {item_id}"}


@router.post("/rebuild")
async def rebuild_wiki():
    items = get_manual_intel_items()

    async def _rebuild():
        for item in items:
            await wiki_builder.process_article(item["id"])

    task = asyncio.create_task(_rebuild())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"ok": True, "message": f"Rebuilding wiki for {len(items)} articles"}


@router.get("/status")
async def get_status():
    concepts = get_wiki_concepts()
    nodes = get_wiki_article_nodes()
    last_sync = max((n.get("wiki_synced_at", "") for n in nodes), default=None) if nodes else None
    return {
        "concept_count": len(concepts),
        "article_count": len(nodes),
        "last_synced_at": last_sync,
    }


@router.get("/concepts")
async def list_concepts():
    concepts = get_wiki_concepts()
    return {"concepts": sorted(concepts, key=lambda c: len(c["article_ids"]), reverse=True)}


@router.delete("/concept/{slug}")
async def remove_concept(slug: str):
    ok = delete_wiki_concept(slug)
    if not ok:
        raise HTTPException(status_code=404, detail="Concept not found")
    return {"ok": True}
```

- [ ] **Step 4: Register wiki router in `backend/main.py`**

After the existing imports block (line 30), add:
```python
from routers.wiki import router as wiki_router
```

After line 71 (`app.include_router(manual_intel_router, ...)`), add:
```python
app.include_router(wiki_router, prefix="/api/wiki", tags=["wiki"])
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python -m pytest tests/test_wiki_router.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
git add backend/routers/wiki.py backend/main.py backend/tests/test_wiki_router.py
git commit -m "feat: add wiki router with sync, rebuild, status, and concept management endpoints"
```

---

## Task 4: Integration + Configuration

**Files:**
- Modify: `backend/routers/manual_intel.py` (trigger wiki after quick_read completes)
- Modify: `.env.example` (document new config keys)

- [ ] **Step 1: Trigger wiki processing from `_run_quick_read`**

In `backend/routers/manual_intel.py`, find the `_run_quick_read` function. After the line that calls `update_manual_intel_item(item_id, {"quick_read": quick_read})`, add the wiki trigger:

Current code at the end of the `try` block in `_run_quick_read`:
```python
        quick_read = (await chat_async([{"role": "user", "content": prompt}])).strip()
        update_manual_intel_item(item_id, {"quick_read": quick_read})
```

Replace with:
```python
        quick_read = (await chat_async([{"role": "user", "content": prompt}])).strip()
        update_manual_intel_item(item_id, {"quick_read": quick_read})
        from services.wiki_builder import process_article
        await process_article(item_id)
```

- [ ] **Step 2: Update `.env.example`**

Append to `/Users/shitaosun/Project/AI-Personal/SignalForge/.env.example`:

```
# LLM Wiki — Obsidian integration
# Set to your Obsidian Vault directory path to enable automatic note writing
# OBSIDIAN_VAULT_PATH=/Users/yourname/Documents/SignalForge-Wiki

# Number of articles referencing a concept before a synthesis note is generated (default: 3)
# WIKI_SYNTHESIS_THRESHOLD=3
```

- [ ] **Step 3: Run all wiki tests together**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge/backend
python -m pytest tests/test_wiki_storage.py tests/test_wiki_builder.py tests/test_wiki_router.py -v
```

Expected: All tests PASS.

- [ ] **Step 4: Manual smoke test**

Add `OBSIDIAN_VAULT_PATH` to your `.env` pointing to a test directory:
```bash
echo "OBSIDIAN_VAULT_PATH=/tmp/signalforge-wiki-test" >> /Users/shitaosun/Project/AI-Personal/SignalForge/.env
```

Start the backend:
```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge/backend
source ../venv/bin/activate
uvicorn main:app --port 8001 --reload
```

Trigger wiki processing for the existing article:
```bash
curl -s -X POST http://localhost:8001/api/wiki/rebuild | python3 -m json.tool
```

Wait ~10 seconds, then check:
```bash
ls /tmp/signalforge-wiki-test/articles/
ls /tmp/signalforge-wiki-test/concepts/
cat /tmp/signalforge-wiki-test/_index.md
```

Expected: `.md` files appear in `articles/` and `concepts/`, `_index.md` lists them.

Check wiki status:
```bash
curl -s http://localhost:8001/api/wiki/status | python3 -m json.tool
```

Expected: `concept_count > 0`, `article_count > 0`.

- [ ] **Step 5: Clean up test vault path from .env**

Remove the temporary OBSIDIAN_VAULT_PATH if you don't want it to auto-sync:
```bash
# Edit .env to set your real Obsidian Vault path or comment out the line
```

- [ ] **Step 6: Commit**

```bash
cd /Users/shitaosun/Project/AI-Personal/SignalForge
git add backend/routers/manual_intel.py .env.example
git commit -m "feat: trigger wiki processing after quick_read completes, document Obsidian config"
```

---

## Self-Review

**Spec coverage:**
- ✅ Manual intel only — `process_article` reads from `get_manual_intel_item_by_id`, triggered only from `manual_intel` router
- ✅ Concept extraction from `content_snippet` — `_extract_concepts(title, content_snippet)` in Task 2
- ✅ Candidate filtering by concept overlap, no LLM — `_find_candidate_articles` in Task 2
- ✅ Deep connection analysis with `content_snippet` of candidates — `_analyze_connections` in Task 2
- ✅ `articles/*.md` written — `_write_article_note` in Task 2
- ✅ `concepts/*.md` written and updated — `_write_concept_note` in Task 2
- ✅ `synthesis/*.md` generated when concept hits threshold — `_maybe_generate_synthesis` in Task 2
- ✅ `_index.md` maintained — `_update_index` in Task 2
- ✅ `OBSIDIAN_VAULT_PATH` config, safe fallback if not set — `_get_vault_path()` in Task 2
- ✅ `WIKI_SYNTHESIS_THRESHOLD` config — `_get_synthesis_threshold()` in Task 2
- ✅ `POST /api/wiki/sync/{item_id}` — Task 3
- ✅ `POST /api/wiki/rebuild` — Task 3
- ✅ `GET /api/wiki/status` — Task 3
- ✅ `GET /api/wiki/concepts` — Task 3
- ✅ `DELETE /api/wiki/concept/{slug}` — Task 3
- ✅ Incremental trigger after quick_read — Task 4, `_run_quick_read` integration
- ✅ Data persisted to `data/wiki/concepts.json` and `data/wiki/article_nodes.json` — Task 1 storage

**Placeholder scan:** No TBDs. All code blocks are complete.

**Type consistency:**
- `upsert_wiki_concept(name, slug, description, article_id)` — called with these 4 args consistently across Task 1 tests, Task 2 `process_article`, and Task 3 tests
- `upsert_wiki_article_node(item_id, slug, concepts, related_articles)` — `concepts` is `List[str]` (concept names), `related_articles` is `List[Dict]` with keys `item_id`, `title`, `reason` — consistent across all tasks
- `get_wiki_article_node(item_id)` returns `Optional[Dict]` with `slug` key — used safely with walrus operator in `process_article`
- `chat_async(messages, provider=None)` — called with `provider="deepseek"` for extraction/connection (cost), no provider override for synthesis (uses default/claude)
