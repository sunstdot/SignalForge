import assert from 'node:assert/strict'
import test from 'node:test'
import { chromium } from 'playwright'

const url = process.env.SIGNAL_FEED_TEST_URL || 'http://localhost:5174'
const x = { id: 'x1', title: 'Agent product idea on X', url: 'https://x.com/example/1', source: 'X', source_type: 'x', summary: 'A new workflow', created_at: '2026-10-10', relevance_score: 9 }
const paper = { ...x, id: 'paper1', title: 'Technical paper', url: 'https://arxiv.org/abs/1', source: 'arXiv', source_type: 'paper' }
const pr = { ...x, id: 'pr1', title: 'Company PR announcement', source: 'Google AI Blog', source_type: 'blog' }

test('daily radar shows both tracks and preserves the complete archive', async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.SIGNAL_FEED_BROWSER || 'chrome' })
  try {
    const page = await browser.newPage()
    await page.route('**/api/**', route => {
      const path = new URL(route.request().url()).pathname
      if (path === '/api/briefing/2026-10-10') {
        return route.fulfill({ json: { date: '2026-10-10', items: [x, paper, pr], signals: {
          inspiration: [{ ...x, so_what: '可以试做新的工作流', why: '一手社区信号' }],
          execution: [{ ...paper, so_what: '值得评估', why: '技术内容' }], total: 2,
        } } })
      }
      if (path === '/api/dates') return route.fulfill({ json: { dates: ['2026-10-10'] } })
      return route.fulfill({ json: {} })
    })
    await page.goto(`${url}/briefing/2026-10-10`)
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByRole('link', { name: x.title }).waitFor()
    assert.match(await radar.innerText(), /可以试做新的工作流/)
    assert.equal(await radar.getByText(paper.title).count(), 0)
    await radar.getByRole('button', { name: /执行雷达/ }).click()
    await radar.getByRole('link', { name: paper.title }).waitFor()
    await page.getByRole('button', { name: /全部内容/ }).click()
    await page.getByText(pr.title).waitFor()
  } finally {
    await browser.close()
  }
})
