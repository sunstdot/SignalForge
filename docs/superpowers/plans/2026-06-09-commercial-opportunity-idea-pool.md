# Commercial Opportunity Idea Pool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users save business opportunity cards from the AI opportunity dashboard into the existing experiment idea pool.

**Architecture:** Add a small payload builder next to the opportunity dashboard so the mapping is independently testable. `OpportunityDashboard.jsx` will call the existing `/api/experiments/ideas` endpoint for business cards only and keep per-card save state in local component state. Existing share-page checkbox behavior remains unchanged.

**Tech Stack:** React 18, Vite, plain CSS, Node built-in `node:test`, existing FastAPI idea endpoint.

---

## File Structure

- Create: `frontend/src/pages/opportunityIdeaPayload.js`
  - Responsibility: Convert normalized business opportunity items into `POST /api/experiments/ideas` request bodies.
- Create: `frontend/src/pages/opportunityIdeaPayload.test.mjs`
  - Responsibility: Verify the opportunity-to-idea payload mapping.
- Modify: `frontend/src/pages/OpportunityDashboard.jsx`
  - Responsibility: Add business-card save state and call the helper/API.
- Modify: `frontend/src/index.css`
  - Responsibility: Style the compact card action row and save status.

## Task 1: Add Tested Payload Builder

**Files:**
- Create: `frontend/src/pages/opportunityIdeaPayload.js`
- Create: `frontend/src/pages/opportunityIdeaPayload.test.mjs`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/opportunityIdeaPayload.test.mjs`:

```js
import assert from 'node:assert/strict'
import test from 'node:test'

import { buildIdeaPayloadFromOpportunity } from './opportunityIdeaPayload.js'

const businessOpportunity = {
  kind: 'business',
  title: 'LLM Token Saver',
  trigger: '开源工具已证明可无损压缩上下文 60-95%。',
  scenario: '帮助使用 GPT 等 LLM 的开发者自动压缩上下文。',
  solution: '免费额度 + 按节省 token 量订阅。',
  features: ['MCP 集成', '云端 API 代理'],
  resistance: '开发者需要信任代理服务。',
  audience: ['独立开发者', '中小团队'],
  totalScore: 19,
  source: 'GitHub Trending',
  sourceTitle: 'Token Saver Repo',
  sourceUrl: 'https://example.com/token-saver',
}

test('buildIdeaPayloadFromOpportunity maps a business opportunity to an idea payload', () => {
  const payload = buildIdeaPayloadFromOpportunity(businessOpportunity, '2026-06-04')

  assert.equal(payload.title, 'LLM Token Saver')
  assert.equal(payload.difficulty, 'medium')
  assert.equal(payload.estimated_days, 7)
  assert.equal(payload.status, 'pending')
  assert.equal(payload.priority, 19)
  assert.equal(payload.briefing_date, '2026-06-04')
  assert.equal(payload.source_type, 'opportunity')
  assert.equal(payload.source_title, 'Token Saver Repo')
  assert.equal(payload.source_url, 'https://example.com/token-saver')
  assert.deepEqual(payload.tags, ['商业机会', '独立开发者', '中小团队'])
})

test('buildIdeaPayloadFromOpportunity includes opportunity details in markdown description', () => {
  const payload = buildIdeaPayloadFromOpportunity(businessOpportunity, '2026-06-04')

  assert.match(payload.description, /\*\*核心洞察\*\*/)
  assert.match(payload.description, /无损压缩上下文/)
  assert.match(payload.description, /\*\*应用场景\*\*/)
  assert.match(payload.description, /自动压缩上下文/)
  assert.match(payload.description, /\*\*商业模式\*\*/)
  assert.match(payload.description, /按节省 token/)
  assert.match(payload.description, /\*\*MVP 功能\*\*/)
  assert.match(payload.description, /- MCP 集成/)
  assert.match(payload.description, /\*\*潜在风险\*\*/)
  assert.match(payload.description, /信任代理服务/)
})

test('buildIdeaPayloadFromOpportunity rejects non-business opportunities', () => {
  assert.equal(
    buildIdeaPayloadFromOpportunity({ kind: 'rdev', title: '需求评审助手' }, '2026-06-04'),
    null,
  )
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && node --test src/pages/opportunityIdeaPayload.test.mjs
```

Expected: FAIL with `Cannot find module ... opportunityIdeaPayload.js`.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/pages/opportunityIdeaPayload.js`:

```js
function normalizeTags(audience = []) {
  return ['商业机会', ...audience.filter(Boolean)]
}

function buildDescription(item) {
  return [
    item.trigger && `**核心洞察**\n${item.trigger}`,
    item.scenario && `**应用场景**\n${item.scenario}`,
    item.solution && `**商业模式**\n${item.solution}`,
    item.features?.length > 0 && `**MVP 功能**\n${item.features.map(feature => `- ${feature}`).join('\n')}`,
    item.resistance && `**潜在风险**\n${item.resistance}`,
  ].filter(Boolean).join('\n\n')
}

export function buildIdeaPayloadFromOpportunity(item, date) {
  if (!item || item.kind !== 'business') return null

  return {
    title: item.title || '未命名商业机会',
    description: buildDescription(item),
    difficulty: 'medium',
    estimated_days: 7,
    tags: normalizeTags(item.audience),
    status: 'pending',
    priority: item.totalScore || 0,
    briefing_date: date,
    source_type: 'opportunity',
    source_title: item.sourceTitle || item.source || '',
    source_url: item.sourceUrl || '',
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && node --test src/pages/opportunityIdeaPayload.test.mjs
```

Expected: PASS, 3 tests passing.

## Task 2: Add Business Card Save Action

**Files:**
- Modify: `frontend/src/pages/OpportunityDashboard.jsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Write the failing source-level test**

Create `frontend/src/pages/OpportunityDashboard.test.mjs`:

```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./OpportunityDashboard.jsx', import.meta.url), 'utf8')

test('OpportunityDashboard imports the opportunity idea payload builder', () => {
  assert.match(source, /buildIdeaPayloadFromOpportunity/)
})

test('OpportunityCard has a separate idea pool action from the share checkbox', () => {
  assert.match(source, /onSaveIdea/)
  assert.match(source, /加入想法池/)
  assert.match(source, /已加入想法池/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && node --test src/pages/OpportunityDashboard.test.mjs
```

Expected: FAIL because `buildIdeaPayloadFromOpportunity`, `onSaveIdea`, and `加入想法池` are not present.

- [ ] **Step 3: Modify `OpportunityDashboard.jsx`**

Add import near the existing imports:

```js
import { buildIdeaPayloadFromOpportunity } from './opportunityIdeaPayload'
```

Add state inside `OpportunityDashboard` near the other state declarations:

```js
const [ideaSaveStates, setIdeaSaveStates] = useState({})
```

Add the save function before `return (`:

```js
async function saveBusinessOpportunityToIdeaPool(item) {
  if (!item || item.kind !== 'business' || ideaSaveStates[item.id] === 'saved' || ideaSaveStates[item.id] === 'saving') return

  const payload = buildIdeaPayloadFromOpportunity(item, date)
  if (!payload) return

  setIdeaSaveStates(prev => ({ ...prev, [item.id]: 'saving' }))
  try {
    const res = await fetch('/api/experiments/ideas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    setIdeaSaveStates(prev => ({ ...prev, [item.id]: 'saved' }))
  } catch (error) {
    console.error('Failed to save opportunity idea:', error)
    setIdeaSaveStates(prev => ({ ...prev, [item.id]: 'error' }))
  }
}
```

Pass props to `OpportunityCard` in the map:

```jsx
onSaveIdea={item.kind === 'business'
  ? (e) => { e.stopPropagation(); saveBusinessOpportunityToIdeaPool(item) }
  : null}
ideaSaveState={ideaSaveStates[item.id]}
```

Update `OpportunityCard` signature:

```js
function OpportunityCard({ item, onOpen, selected = false, onToggle, onSaveIdea, ideaSaveState }) {
```

Add the button after the footer:

```jsx
{onSaveIdea && (
  <div className="opportunity-card-actions">
    <button
      type="button"
      className="opportunity-idea-button"
      onClick={onSaveIdea}
      disabled={ideaSaveState === 'saving' || ideaSaveState === 'saved'}
    >
      {ideaSaveState === 'saving' ? '加入中...' : ideaSaveState === 'saved' ? '已加入想法池' : '加入想法池'}
    </button>
    {ideaSaveState === 'error' && <span>保存失败，请重试</span>}
  </div>
)}
```

- [ ] **Step 4: Add CSS**

Append near the opportunity dashboard CSS in `frontend/src/index.css`:

```css
.opportunity-card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 32px;
}

.opportunity-idea-button {
  border: 1px solid var(--accent-blue);
  background: white;
  color: var(--accent-blue);
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
}

.opportunity-idea-button:hover:not(:disabled) {
  background: #eff6ff;
}

.opportunity-idea-button:disabled {
  border-color: var(--border);
  background: var(--bg-secondary);
  color: var(--text-muted);
  cursor: default;
}

.opportunity-card-actions span {
  font-size: 12px;
  color: #dc2626;
}
```

- [ ] **Step 5: Run tests to verify this task passes**

Run:

```bash
cd frontend && node --test src/pages/OpportunityDashboard.test.mjs src/pages/opportunityIdeaPayload.test.mjs
```

Expected: PASS.

## Task 3: Verify Build and Existing Focused Tests

**Files:**
- No new files.

- [ ] **Step 1: Run focused frontend tests**

Run:

```bash
cd frontend && node --test src/pages/*.test.mjs
```

Expected: PASS for existing and new page tests.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend && pnpm build
```

Expected: Vite build completes without errors.

- [ ] **Step 3: Inspect changed files**

Run:

```bash
git diff -- frontend/src/pages/OpportunityDashboard.jsx frontend/src/pages/opportunityIdeaPayload.js frontend/src/pages/opportunityIdeaPayload.test.mjs frontend/src/pages/OpportunityDashboard.test.mjs frontend/src/index.css
```

Expected: Diff only contains the helper, tests, card action UI, save API call, and related CSS.

## Self-Review

- Spec coverage: Task 1 covers payload mapping and non-business rejection. Task 2 covers the card action, saved/error states, and separation from the share checkbox. Task 3 covers verification.
- Placeholder scan: No `TBD`, `TODO`, or unspecified implementation steps.
- Type consistency: The helper name is `buildIdeaPayloadFromOpportunity` in tests and implementation. `OpportunityCard` props use `onSaveIdea` and `ideaSaveState` consistently.
