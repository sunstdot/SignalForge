# Changelog

## 0.1.4 — 2026-11-08

- Fixed `paper-reading` skill loading: runtime skills now declare the required `source` string.
- Verified the skill loads through the Harness skill tool and returns the full paper-reading protocol.
- No source-analysis or UI behavior changes.

## 0.1.3 — 2026-11-07

- Expanded from 17 to **28 sources**, including 15 official AI company blogs.
- Added RSS/Atom sources: Google Research, NVIDIA Developer, Apple Machine Learning, LangChain, Cloudflare AI, AWS Machine Learning.
- Added HTML-adapted sources for sites without RSS: Anthropic News, Anthropic Engineering, Cognition, Meta AI, Cohere.
- Official blog lookback is now 14 days (news/community remain 48 hours), so weekly-updated labs still appear.
- Model candidate pool raised to 72, with per-source caps, a 24-official cap, and round-robin source diversification so one company cannot dominate.
- Source fetch retries once on transient network failures.
- Updated README source list and categories.

## 0.1.2 — 2026-11-06

- Added a host-registered **paper-reading** skill with the full "papers are compressed arguments" protocol and a fixed Chinese output contract.
- Paper cards now show **精读论文** next to 继续对话; it opens a new conversation with the paper title, URL, abstract, and intel quick-read already in the composer.
- Added a collapsed **论文精读** panel above the tabs for papers outside the digest: paste an arXiv / DOI / PDF link, or a title + abstract.
- The paper prompt tells the agent to fetch full text first, mark unavailable evidence instead of inventing it, and not pretend to inspect figure pixels.
- Added regression coverage for article→chat, paper→chat, and manual paper/DOI normalization.

## 0.1.1 — 2026-11-05

- Added **继续对话 / Discuss with AI** to every signal and candidate card.
- The button opens a new Harness conversation with the title, URL, source, category, Chinese quick-read, evidence, summary, and key details already in the composer.
- If no workspace/conversation service is available, the full prompt is copied to the clipboard with a notice.
- Includes a local regression test for the article-to-chat prompt and `startSession` call.

## 0.1.0 — 2026-11-04

First public release.

- Sidebar panel with three tabs: selected signals, business/engineering opportunities, and every fetched candidate.
- 17 login-free sources: Hacker News, arXiv, Hugging Face Daily Papers, GitHub Trending, official AI blogs, newsletters, and media.
- Two-stage AI analysis on the signed-in DeepSeek account:
  - select at most 5 signals with Chinese “what was found / why it matters / evidence” cards;
  - write 3 business + 3 engineering opportunities from those signals.
- Chinese quick-reads for every candidate, with category tags (paper, repository, model, news, AI company blog, WeChat official account, Smol news, investor news).
- Full candidate list with search, category filters, original links, and expandable details.
- One digest per day under `$DSH_HOME/signalforge`; dates without signals are hidden.
- Optional import of already-generated SignalForge briefings for historical dates.
