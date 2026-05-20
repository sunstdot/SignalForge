# LLM Wiki + Obsidian Integration Design

**Date:** 2026-05-20  
**Status:** Approved  
**Scope:** Manual intel articles only (`data/manual_intel/`). Auto-crawled content (`data/content/`) is excluded.

---

## Overview

Build an LLM-powered personal wiki that processes manually entered articles, extracts knowledge concepts, discovers connections between articles, and writes structured Markdown notes directly into an Obsidian Vault. The system surfaces hidden knowledge patterns that don't appear in any single article.

---

## Architecture

```
SignalForge Backend
  ├── services/wiki_builder.py     ← Core LLM Wiki engine
  ├── routers/wiki.py              ← API: /api/wiki/*
  └── data/wiki/
        ├── concepts.json          ← Concept node index (persisted)
        └── article_nodes.json     ← Per-article Wiki metadata

Obsidian Vault (path configured via .env)
  ├── articles/
  │     └── {title-slug}.md       ← One note per article
  ├── concepts/
  │     └── {concept-slug}.md     ← Concept node notes
  ├── synthesis/
  │     └── {concept-slug}-synthesis.md  ← Auto-generated when ≥3 articles share a concept
  └── _index.md                   ← Map of Content (auto-maintained)
```

**Trigger chain (incremental mode):**

```
New article created → AI analysis completes (_run_quick_read)
  → asyncio.create_task(wiki_builder.process_article(item_id))
      Step 1: Concept extraction  (content_snippet, 6000 chars)
      Step 2: Candidate filtering (concept overlap, no LLM)
      Step 3: Deep connection analysis (content_snippet of new + candidate articles)
      Step 4: Write Obsidian .md files
      Step 5: Synthesis trigger check (concept referenced ≥ WIKI_SYNTHESIS_THRESHOLD times)
      Step 6: Update _index.md
```

**Batch rebuild (future):**  
`POST /api/wiki/rebuild` → Re-runs full pipeline for all manual intel articles, rebuilds entire Vault.

---

## Data Structures

### `data/wiki/concepts.json`
```json
[
  {
    "name": "In-Context Learning",
    "slug": "in-context-learning",
    "description": "模型无需微调，通过 prompt 中的示例学习新任务的能力",
    "article_ids": ["uuid-1", "uuid-3"],
    "created_at": "2026-05-20T10:00:00",
    "updated_at": "2026-05-20T12:00:00"
  }
]
```

### `data/wiki/article_nodes.json`
```json
[
  {
    "item_id": "uuid-1",
    "slug": "learning-beyond-gradients",
    "concepts": ["In-Context Learning", "Meta-Learning"],
    "related_articles": [
      { "item_id": "uuid-3", "reason": "都探讨了无梯度学习的边界" }
    ],
    "wiki_synced_at": "2026-05-20T10:00:00"
  }
]
```

### Obsidian article note: `articles/{slug}.md`
```markdown
---
title: Learning Beyond Gradients
url: https://...
platform: Blog
added: 2026-05-20
concepts: [In-Context Learning, Meta-Learning]
---

## 速读摘要
{quick_read content}

## 我的点评
{user_note content}

## 知识关联
- [[In-Context Learning]] — 文章核心概念
- [[Meta-Learning]] — 从元学习视角分析梯度替代方案

## 关联文章
- [[another-article-slug]] — 都探讨了无梯度学习的边界
```

### Obsidian concept note: `concepts/{slug}.md`
```markdown
---
type: concept
article_count: 2
updated: 2026-05-20
---

## 定义
{LLM-generated one-sentence definition}

## 引用此概念的文章
- [[learning-beyond-gradients]]
- [[another-article-slug]]

## 相关概念
- [[Meta-Learning]]
- [[Few-Shot Learning]]
```

### Obsidian synthesis note: `synthesis/{slug}-synthesis.md`
```markdown
---
type: synthesis
concept: In-Context Learning
article_count: 3
generated: 2026-05-20
---

## 核心定义与当前认知边界
...

## 不同视角与争议
...

## 跨文章隐含规律
（在任何单篇文章中都没有显式出现的结论）
...

## 值得继续关注的开放问题
...
```

---

## LLM Prompts

### Step 1 — Concept Extraction
- **Input:** title + content_snippet (6000 chars)
- **Model:** deepseek (cost-efficient)
- **Output:** `[{"name": "...", "description": "..."}]`

```
从以下文章中提取 5-10 个核心知识概念或技术实体。
概念要求：
- 用英文或中文，保持专业术语一致性（如 "RAG" 不要写成 "检索增强生成"）
- 粒度适中，不要太宽泛（"AI" 不是概念），不要太具体（"GPT-4o 的温度参数" 不是概念）
- 每个概念附一句话定义

文章标题：{title}
文章内容：{content_snippet}

输出严格 JSON，不要 markdown 代码块：
[{"name": "...", "description": "..."}]
```

### Step 2 — Candidate Filtering (no LLM)
- Find existing articles that share at least one concept with the new article
- These become candidates for deep connection analysis
- If 0 candidates: skip Step 3, only write Obsidian note with concepts

### Step 3 — Deep Connection Analysis
- **Input:** new article content_snippet + candidate articles' content_snippets (typically 3-5 articles)
- **Model:** deepseek
- **Output:** connection JSON

```
你是一个知识图谱构建助手。

新文章：{title}
新文章内容：{content_snippet}

候选关联文章：
[文章1标题]
{文章1 content_snippet}

[文章2标题]
{文章2 content_snippet}

任务：
1. 从候选文章中找出与新文章有实质关联的文章（可以是 0 篇），说明关联原因（超越共享概念的深层主题联系）
2. 识别新文章引入了哪些候选文章中没有的新概念角度

输出严格 JSON，不要 markdown 代码块：
{
  "related_articles": [{"title": "...", "reason": "..."}],
  "additional_insights": "跨文章发现的额外洞察（可为空字符串）"
}
```

### Step 4 — Synthesis Note Generation (triggered when concept hits threshold)
- **Input:** concept name + content_snippets of all articles referencing it
- **Model:** claude (higher quality for synthesis)
- **Output:** Markdown synthesis note body

```
以下 {N} 篇文章都涉及概念「{concept}」：

[文章1标题]
{文章1 content_snippet}

[文章2标题]
{文章2 content_snippet}
...

请综合这些文章，生成一篇「{concept}」的知识合成笔记，包含：
1. 核心定义与当前认知边界
2. 这些文章呈现了哪些不同视角或争议
3. 跨文章发现的隐含规律（在任何单篇文章中都没有显式出现的结论）
4. 值得继续关注的开放问题

用中文输出，Markdown 格式，不要输出 frontmatter。
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/wiki/sync/{item_id}` | Trigger incremental Wiki build for one article (called internally after AI analysis) |
| `POST` | `/api/wiki/rebuild` | Full Vault rebuild for all manual intel articles |
| `GET` | `/api/wiki/status` | Sync status: concept count, article count, last sync time |
| `GET` | `/api/wiki/concepts` | List all concept nodes with reference counts |
| `DELETE` | `/api/wiki/concept/{slug}` | Remove a concept node (manual cleanup) |

---

## Configuration

Add to `.env`:
```
OBSIDIAN_VAULT_PATH=/Users/shitaosun/Documents/SignalForge-Wiki
WIKI_SYNTHESIS_THRESHOLD=3
```

If `OBSIDIAN_VAULT_PATH` is not set, the wiki builder logs a warning and skips file writing (safe fallback).

---

## Connection Logic Summary

Article-to-article connections have two layers:

1. **Concept-mediated (automatic, no LLM):** Articles sharing a concept are implicitly connected through the concept node. Obsidian backlinks handle this automatically.

2. **Direct thematic (LLM-judged):** After concept-overlap filtering identifies candidates, LLM compares full content_snippets to find connections beyond shared concepts (e.g., contradicting conclusions, implementation of a theory, complementary case studies).

---

## Constraints

- Only manual intel items (`data/manual_intel/`) are processed. Auto-crawled content is excluded.
- Token budget per connection analysis: ~1 new article (6000 chars) + up to 5 candidates (6000 chars each) = ~36,000 chars ≈ manageable with deepseek's context window.
- Synthesis is only triggered when a concept reaches `WIKI_SYNTHESIS_THRESHOLD` (default: 3) article references, preventing premature synthesis on sparse data.
