import assert from 'node:assert/strict'
import test from 'node:test'
import { chromium } from 'playwright'

const base = process.env.SIGNAL_FEED_TEST_URL || 'http://127.0.0.1:5176'
const day = '2026-10-13'
const raw = { id: 'x-account-1', source: 'X:@oran_ge', source_type: 'x',
  title: 'My technical note', url: 'https://x.com/oran_ge/status/2109821043506610569',
  summary: 'Published a reproducible agent workflow.', created_at: day, relevance_score: 9 }

async function showBriefing(data, check) {
  const browser = await chromium.launch({ headless: true, channel: process.env.SIGNAL_FEED_BROWSER || 'chrome' })
  try {
    const page = await browser.newPage()
    let apiCalls = 0
    await page.route('**/api/**', route => {
      const pathname = new URL(route.request().url()).pathname
      if (pathname === `/api/briefing/${day}`) { apiCalls++; return route.fulfill({ json: data }) }
      if (pathname === '/api/dates') return route.fulfill({ json: { dates: [day] } })
      return route.fulfill({ json: {} })
    })
    await page.goto(`${base}/briefing/${day}`, { waitUntil: 'domcontentloaded', timeout: 10000 })
    await page.getByRole('heading', { name: '今日信号' }).waitFor({ timeout: 25000 })
    await check(page, () => apiCalls)
  } finally {
    await browser.close()
  }
}

test('default account section shows quote/original link and unavailable account without inventing posts', async () => {
  await showBriefing({ date: day, items: [raw], signals: {
    inspiration: [], execution: [], total: 0,
    accounts: [
      { handle: '@oran_ge', status: 'partial', checked_at: `${day}T12:00:00Z`,
        posts: [{ id: raw.id, handle: '@oran_ge', kind: 'quote', title: raw.title,
          url: raw.url, published_at: `${day}T01:38:30Z`, takeaway: 'A working agent workflow.',
          quoted_url: 'https://x.com/other/status/2109533044407439607' }] },
      { handle: '@dotey', status: 'unavailable', checked_at: `${day}T12:00:00Z`, reason: 'http_429', posts: [] },
    ],
    events: [{ id: 'event-1', title: 'Agent Compiler launched',
      what_happened: 'Official source was published.', why_read: 'Reproducible benchmark available.',
      sources: [{ url: 'https://example.com/compiler', title: 'Original project' }],
      discussions: { x: { status: 'unavailable', posts: [] },
        hn: { status: 'no_results', posts: [] }, reddit: { status: 'unavailable', posts: [] } } }],
  } }, async (page, calls) => {
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByRole('button', { name: /关注账号/ }).waitFor({ timeout: 5000 })
    await radar.getByRole('link', { name: /查看原帖/ }).waitFor({ timeout: 5000 })
    assert.match(await radar.innerText(), /@oran_ge.*引用帖/s)
    assert.match(await radar.innerText(), /@dotey.*采集不可用/s)
    assert.equal(await radar.getByRole('link', { name: /查看原帖/ }).count(), 1)
    assert.equal(await radar.getByRole('heading', { name: 'Agent Compiler launched' }).count(), 0)
    const before = calls()
    await radar.getByRole('button', { name: /事件追踪/ }).click()
    await radar.getByRole('heading', { name: 'Agent Compiler launched' }).waitFor()
    await page.getByRole('button', { name: /全部内容/ }).click()
    await page.getByText(raw.title).waitFor()
    assert.equal(calls(), before)
  })
})

test('legacy day without account state retains old signal tracks', async () => {
  await showBriefing({ date: day, items: [raw], signals: {
    inspiration: [{ ...raw, takeaway: 'Original note.' }], execution: [], total: 1,
  } }, async page => {
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByRole('button', { name: /灵感雷达/ }).waitFor({ timeout: 5000 })
    assert.equal(await radar.getByRole('button', { name: /关注账号/ }).count(), 0)
    assert.equal(await radar.getByRole('link', { name: raw.title }).count(), 1)
  })
})
