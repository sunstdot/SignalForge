"""LLM Wiki Builder — processes manual intel articles into Obsidian notes."""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import services.storage as _storage
from services.llm_client import chat_async
from services.storage import (
    get_wiki_concepts,
    get_wiki_article_nodes,
    get_wiki_article_node,
    upsert_wiki_concept,
    upsert_wiki_article_node,
)


def get_manual_intel_item_by_id(item_id: str):
    """Thin wrapper so monkeypatching services.storage.get_manual_intel_item_by_id works in tests."""
    return _storage.get_manual_intel_item_by_id(item_id)


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
文章内容：{content_snippet[:6000]}

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

新文章：{new_item.get('title', '')}
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
    concept_names = ", ".join(f'"{c["name"].replace(chr(34), chr(39))}"' for c in concepts)

    content = f"""---
title: "{item['title'].replace('"', "'")}"
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

    synthesis_dir = vault_path / "synthesis"
    synthesis_file = synthesis_dir / f"{concept['slug']}-synthesis.md"
    if synthesis_file.exists():
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
    # 用 quick_read（AI 摘要，必定存在）+ content_snippet 作为输入：X/推文等无法服务端抓取的
    # 来源 content_snippet 往往只剩署名行，仅靠它会提取不到概念。quick_read 在前，保证核心内容
    # 不会被 prompt 的长度截断丢掉。
    concept_source = "\n\n".join(
        part for part in [item.get("quick_read", ""), item.get("content_snippet", "")] if part
    )
    concepts = await _extract_concepts(item.get("title", ""), concept_source)
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
