# Xiaohongshu Share Page Design

## Goal

Create a Xiaohongshu-ready share artifact from existing SignalForge data using the workflow style of `html-anything`:

- SignalForge selects and prepares the content.
- An HTML generation layer turns that content into publishable 3:4 cards.
- The output can be previewed as HTML and exported as PNG images.

The first target format is a three-page carousel:

1. One page of high-scoring business opportunities.
2. Two pages of high-quality AI briefing items.

## Why `html-anything`

`html-anything` is best treated as an HTML-first publishing workflow rather than a runtime UI dependency. Its useful ideas for this feature are:

- template-driven generation for specific delivery surfaces such as Xiaohongshu cards;
- single-file HTML as the editable source artifact;
- export to PNG after visual review;
- AI-assisted composition over structured source content.

SignalForge should not embed the repository as an application dependency. Instead, it should reuse the same pattern:

1. prepare structured content;
2. render a share-oriented HTML artifact;
3. preview and export.

## Data Sources

### Business opportunities

Source file:

- `data/opportunities/YYYY-MM-DD.json`

Fields used:

- `opportunity_title`
- `total_score`
- `core_insight`
- `product_form`
- optional product/category fields when available

Initial selection rule:

- sort by `total_score` descending;
- take the top 3 by default;
- keep the design flexible for 3-5 items later.

### AI briefing items

Source files:

- `data/content/YYYY-MM-DD.json`
- `data/quick_reads/YYYY-MM-DD.json`

Fields used from content items:

- `id`
- `title`
- `source`
- `source_type`
- `relevance_score`

Fields used from quick reads:

- existing quick-read markdown summary for each selected item.

Initial selection rule:

- select 5 items;
- prefer source diversity so one source type does not dominate the carousel;
- use the existing quick-read content directly instead of generating a second summary layer.

## Page Structure

### Page 1: Business opportunities

Purpose:

- show the most actionable opportunities first;
- let a reader quickly understand what can be built.

Content:

- title;
- short subtitle;
- 3 opportunity cards;
- each card contains:
  - rank;
  - title;
  - score;
  - concise explanation derived from existing opportunity fields;
  - category tag.

Layout rule:

- rank, title, and score remain on the same visual row.

### Pages 2-3: AI briefing items

Purpose:

- preserve useful detail from existing quick reads without overcrowding a single card;
- give the reader a lightweight but meaningful daily intelligence digest.

Content:

- 2-3 briefing cards per page;
- each card contains:
  - rank;
  - title;
  - source type;
  - quick-read sections already produced by SignalForge:
    - core content;
    - key points;
    - why it matters.

Layout rule:

- if five selected items do not fit comfortably on one page, split across two pages rather than collapsing or truncating the content.

## Visual Direction

- Format: 3:4 vertical Xiaohongshu cards.
- Tone: editorial and work-focused rather than decorative.
- Page count for the initial version: 3.
- Visual hierarchy:
  - strong page title;
  - restrained subtitle;
  - card-based item list;
  - minimal footer with brand and date or page count.
- Color:
  - warm neutral base for business opportunities;
  - cooler accent for AI briefing pages;
  - restrained palette with high readability.

## Proposed Flow

1. User chooses a date.
2. SignalForge loads business opportunities, content items, and quick reads for that date.
3. A share payload is assembled from the selected records.
4. The payload is rendered into a three-page HTML artifact.
5. User previews the artifact.
6. The artifact can be exported as PNG images for posting.

## Components

### Content selector

Responsibilities:

- choose the top business opportunities;
- choose diversified briefing items;
- attach quick-read content to briefing items;
- return a normalized share payload.

### HTML renderer

Responsibilities:

- map the normalized payload into the three-page card layout;
- enforce card order, visual structure, and page splitting;
- produce a standalone HTML artifact suitable for preview and export.

### Export step

Responsibilities:

- capture each 3:4 page as a PNG;
- preserve consistent dimensions and typography.

## Non-goals

- No interactive expand/collapse in the first release.
- No additional AI rewrite pass for briefing items while quick reads already exist.
- No attempt to turn `html-anything` into a bundled dependency of the SignalForge web app.
- No broad redesign of the existing briefing or opportunity pages.

## Risks and Decisions

### Quick-read length

Decision:

- preserve the existing quick-read content;
- split content across more pages if needed rather than introducing interaction into a static-share artifact.

### Content diversity

Decision:

- briefing selection must avoid a page made entirely from one source type when sufficiently good alternatives exist.

### Delivery surface

Decision:

- optimize for Xiaohongshu image output first;
- HTML preview is an intermediate artifact, not the final publishing surface.

## Validation

The feature is successful when:

- one date can produce a consistent three-page artifact;
- page 1 shows the selected opportunities clearly;
- pages 2-3 preserve readable quick-read content without crowding;
- each page exports cleanly to PNG at the intended aspect ratio;
- the generated content matches the source data for the selected date.
