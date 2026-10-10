# Venture Radar Intelligence Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn venture radar funding candidates into evidence-aware intelligence while keeping new product launches visible through a lighter product-specific gate.

**Architecture:** Keep raw reports immutable, normalize them at read/import time into product and funding events, and use one normalized contract for stage feeds, quality metrics, generic content import, and card rendering. Funding verification is evidence-gated; product launches only require a named product and a source-backed discovery record.

**Tech Stack:** Python 3, file-backed JSON reports, `unittest`, React, Vite, Node `node:test`.

## Global Constraints

- Funding stages are `candidate`, `watchlist`, `verified`, and `rejected`.
- Product launches do not inherit the strict funding verification gate.
- Valuation never becomes `amount_raised`; publication time never becomes financing time.
- Candidate and rejected events never enter the generic user-facing content feed.
- Empty funding facts stay hidden and missing facts render as one evidence-gap line.

---

### Task 1: Funding Contract and Admission Rules

**Files:**
- Modify: `backend/services/venture_radar_intelligence.py`
- Test: `backend/tests/test_venture_radar_intelligence.py`

**Interfaces:**
- Consumes: raw `funding_rounds`, `products`, and report-level `source_links`.
- Produces: `normalize_funding_event(raw, report)`, `normalize_product_launch(raw, report)`, and `normalize_report(report)`.

- [x] Add failing tests for provenance objects, speculative-title precedence, official-source classification, duplicate rejection, and meaningful analysis fallback.
- [x] Run the focused backend test module and confirm the new tests fail for the expected reasons.
- [x] Preserve field-level provenance, derive conservative status/date values, calculate evidence-aware scores, and reject duplicate normalized events.
- [x] Run the focused backend test module and confirm it passes.

### Task 2: Enrichment and Downstream Import

**Files:**
- Modify: `backend/services/venture_radar_intelligence.py`
- Modify: `backend/services/venture_product_radar_importer.py`
- Test: `backend/tests/test_venture_product_radar_importer.py`

**Interfaces:**
- Consumes: normalized intelligence events and report context.
- Produces: structured verification tasks plus generic content items derived from normalized values.

- [x] Add failing tests proving normalized funding values and stages reach downstream content without legacy `amount`/date ambiguity.
- [x] Run importer tests and confirm the new tests fail.
- [x] Generate the ten funding enrichment task categories, require Wingsbot to execute and record task results where possible, and import only verified generic content while preserving watchlist events in report archives.
- [x] Run importer tests and confirm they pass.

### Task 3: Card Information Architecture

**Files:**
- Modify: `frontend/src/pages/ventureRadarText.js`
- Modify: `frontend/src/pages/VentureRadarPage.jsx`
- Test: `frontend/src/pages/ventureRadarText.test.mjs`
- Test: `frontend/src/pages/VentureRadarPage.test.mjs`

**Interfaces:**
- Consumes: normalized funding/product events.
- Produces: compact Chinese card sections with visible facts, evidence, sources, and follow-up items.

- [x] Add failing tests for Chinese labels, type/stage separation, source links, title preference, and hidden empty facts.
- [x] Run frontend tests and confirm the new tests fail.
- [x] Render complete titles, event status/confidence/sector tags, Chinese analysis labels, compact facts, evidence status, source links, and one consolidated evidence-gap line.
- [x] Run frontend tests and confirm they pass.

### Task 4: End-to-End Verification

**Files:**
- Verify: `backend/tests/test_venture_radar_intelligence.py`
- Verify: `backend/tests/test_venture_product_radar_importer.py`
- Verify: `frontend/src/pages/VentureRadarPage.test.mjs`

- [x] Normalize the archived Colossal Biosciences event and inspect its exact stage, status, amount, valuation, date, confidence, and gaps.
- [x] Run all venture radar backend tests.
- [x] Run all venture radar frontend tests.
- [x] Run the frontend production build and report unrelated pre-existing warnings separately.
