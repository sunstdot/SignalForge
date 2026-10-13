import assert from 'node:assert/strict'
import test from 'node:test'
import { chromium } from 'playwright'

const url = process.env.SIGNAL_FEED_TEST_URL || 'http://localhost:5175'
const date = '2026-10-13'
const source = { id: 'blog-1', title: 'Original blog report', url: 'https://example.com/compiler',
  source: 'Official', source_type: 'blog', summary: 'Verified source', created_at: date, relevance_score: 8 }

async function withBriefing(data, run) {
  const browser = await chromium.launch({ headless: true, channel: process.env.SIGNAL_FEED_BROWSER || 'chrome' })
  try {
    const page = await browser.newPage()
    let briefingRequests = 0
    await page.route('**/api/**', route => {
      const pathname = new URL(route.request().url()).pathname
      if (pathname === `/api/briefing/${date}`) {
        briefingRequests++
        return route.fulfill({ json: data })
      }
      if (pathname === '/api/dates') return route.fulfill({ json: { dates: [date] } })
      return route.fulfill({ json: {} })
    })
    await page.goto(`${url}/briefing/${date}`, { waitUntil: 'domcontentloaded', timeout: 10000 })
    await page.getByRole('heading', { name: '今日信号' }).waitFor({ timeout: 25000 })
    await run(page, () => briefingRequests)
  } finally {
    await browser.close()
  }
}

test('today shows cached events, independent platform coverage and all original content', async () => {
  await withBriefing({ date, items: [source], signals: {
    inspiration: [], execution: [], total: 0,
    source_status: { hn: 'ok', reddit: { 'r/ClaudeAI': 'unavailable' } },
    events: [{ id: 'event-compiler', title: 'Agent Compiler released',
      what_happened: 'Agent Compiler published its source.', why_read: 'Developers can inspect its implementation.',
      sources: [{ url: source.url, source: 'Official', title: source.title }],
      discussions: { x: { status: 'unavailable', posts: [] },
        hn: { status: 'found', posts: [{ url: 'https://news.ycombinator.com/item?id=456', title: 'Independent test' }] },
        reddit: { status: 'no_results', posts: [] } } }],
  } }, async (page, requests) => {
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByRole('heading', { name: 'Agent Compiler released' }).waitFor({ timeout: 15000 })
    assert.match(await radar.innerText(), /发生了什么.*Agent Compiler published its source/s)
    assert.match(await radar.innerText(), /值得看什么.*Developers can inspect its implementation/s)
    assert.match(await radar.innerText(), /X.*不可用/s)
    assert.match(await radar.innerText(), /Reddit.*未找到讨论/s)
    assert.equal(await radar.getByRole('link', { name: source.title }).count(), 1)
    assert.equal(await radar.getByRole('link', { name: 'Independent test' }).count(), 1)
    const requestsBeforeTabSwitch = requests() // Vite's React.StrictMode can fetch twice on mount.
    await page.getByRole('button', { name: /全部内容/ }).click()
    await page.getByText(source.title).waitFor()
    assert.equal(requests(), requestsBeforeTabSwitch)
  })
})

test('collection-only date says selection has not run rather than no events occurred', async () => {
  await withBriefing({ date, items: [source], signals: {
    inspiration: [], execution: [], total: 0,
    events: [], source_status: { hn: 'ok', reddit: {} }, selection_status: 'not_run',
  } }, async page => {
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByText(/事件筛选尚未运行/).waitFor({ timeout: 15000 })
    assert.doesNotMatch(await radar.innerText(), /没有足够原始依据的具体事件/)
  })
})

test('old briefing without event cache still displays original inspiration and execution', async () => {
  await withBriefing({ date, items: [source], signals: {
    inspiration: [{ ...source, takeaway: 'Verified builder report' }], execution: [], total: 1,
  } }, async page => {
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByRole('button', { name: /灵感雷达/ }).waitFor({ timeout: 15000 })
    await radar.getByRole('link', { name: source.title }).waitFor()
    assert.equal(await radar.getByRole('heading', { name: 'Agent Compiler released' }).count(), 0)
  })
})
