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
          inspiration: [{ ...x, takeaway: '开发者发布了可复现的 Agent 工作流和公开测试结果。',
            facts: ['提供公开的基准测试', '披露了失败案例'],
            so_what: '可以对照现有流程评估是否值得试用。', evidence: '32 likes, 8 replies' }],
          execution: [{ ...paper, takeaway: '论文提供新的 Agent 评估方法和复现实验。',
            so_what: '可以用来检查现有 Agent 的可靠性。', evidence: '' }], total: 2,
        } } })
      }
      if (path === '/api/dates') return route.fulfill({ json: { dates: ['2026-10-10'] } })
      return route.fulfill({ json: {} })
    })
    await page.goto(`${url}/briefing/2026-10-10`)
    const radar = page.getByRole('region', { name: '今日信号' })
    await radar.getByRole('link', { name: x.title }).waitFor()
    assert.match(await radar.innerText(), /发生了什么.*开发者发布了可复现的 Agent 工作流/s)
    assert.match(await radar.innerText(), /关键信息.*提供公开的基准测试/s)
    assert.match(await radar.innerText(), /值得看什么.*可以对照现有流程评估/s)
    assert.match(await radar.innerText(), /32 likes, 8 replies/)
    assert.equal(await radar.getByRole('link', { name: /查看原文/ }).count(), 1)
    assert.equal(await radar.getByText(paper.title).count(), 0)
    await radar.getByRole('button', { name: /执行雷达/ }).click()
    await radar.getByRole('link', { name: paper.title }).waitFor()
    await page.getByRole('button', { name: /全部内容/ }).click()
    await page.getByText(pr.title).waitFor()
  } finally {
    await browser.close()
  }
})
