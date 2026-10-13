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

test('event and followed account evidence are both visible in event-first reading order', async () => {
  await withBriefing({ date, items: [source], signals: {
    inspiration: [], execution: [], total: 0,
    events: [{ id: 'event-compiler', title: 'Agent Compiler released',
      what_happened: 'A verified release.', why_read: 'Inspect the source.',
      sources: [{ url: source.url, title: source.title }], discussions: {} }],
    accounts: [{ handle: '@oran_ge', status: 'partial', checked_at: `${date}T12:00:00Z`,
      posts: [{ id: 'post-1', kind: 'original', title: 'Independent account note',
        url: 'https://x.com/oran_ge/status/2109821043506610569' }] }],
  } }, async page => {
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByRole('heading', { name: 'Agent Compiler released' }).waitFor({ timeout: 15000 })
    await radar.getByRole('heading', { name: '关注账号' }).waitFor({ timeout: 15000 })
    assert.equal(await radar.getByRole('link', { name: /查看原帖/ }).count(), 1)
    const headings = await radar.locator('h3').allTextContents()
    assert.ok(headings.indexOf('事件追踪') < headings.indexOf('关注账号'))
  })
})

test('daily summary is secondary and source categories appear only in the archive', async () => {
  await withBriefing({ date, summary: 'A concise summary of this daily briefing.', items: [source],
    signals: { inspiration: [], execution: [], total: 0, events: [], accounts: [] } }, async page => {
    assert.equal(await page.getByText('A concise summary of this daily briefing.').isVisible(), false)
    assert.equal(await page.getByRole('button', { name: /论文/ }).count(), 0)
    await page.getByText('日报总览').click()
    await page.getByText('A concise summary of this daily briefing.').waitFor()
    await page.getByRole('button', { name: /全部内容/ }).click()
    await page.getByRole('button', { name: /论文/ }).waitFor()
    await page.getByText(source.title).waitFor()
  })
})

test('narrow screens keep the signal content readable and provide a way back to navigation', async () => {
  await withBriefing({ date, items: [source], signals: {
    inspiration: [], execution: [], total: 0,
    events: [{ id: 'event-compiler', title: 'Agent Compiler released',
      what_happened: 'A verified release.', why_read: 'Inspect the source.',
      sources: [{ url: source.url, title: source.title }], discussions: {} }],
    accounts: [{ handle: '@oran_ge', status: 'unavailable', posts: [] }],
  } }, async page => {
    await page.setViewportSize({ width: 390, height: 844 })
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByRole('heading', { name: 'Agent Compiler released' }).waitFor()
    assert.ok((await radar.boundingBox()).width >= 300, 'signal region should use the phone viewport')
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
    const accountJump = radar.getByRole('link', { name: '查看关注账号' })
    assert.equal(await accountJump.isVisible(), true)
    await accountJump.click()
    const accountPosition = await radar.getByRole('heading', { name: '关注账号' }).boundingBox()
    assert.ok(accountPosition.y >= 0 && accountPosition.y < 844, 'account section should be in view after the jump')
    const menu = page.getByRole('button', { name: '打开导航' })
    assert.equal(await menu.isVisible(), true)
    await menu.click()
    assert.equal(await page.getByRole('link', { name: /情报搜索/ }).isVisible(), true)
    await page.keyboard.press('Escape')
    assert.equal(await page.getByRole('button', { name: '打开导航' }).isVisible(), true)
    assert.equal(await page.getByRole('link', { name: /情报搜索/ }).isVisible(), false)
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
