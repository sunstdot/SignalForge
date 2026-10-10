import assert from 'node:assert/strict'
import { mkdirSync } from 'node:fs'
import test from 'node:test'
import { chromium } from 'playwright'

const baseURL = process.env.PAPER_READ_TEST_URL || 'http://localhost:5174'
const paper = {
  id: 'paper-browser-test', title: 'Agensh: Scaling Organizational Intelligence to 1,024 Agents',
  source_type: 'paper', source: 'HuggingFace Papers', url: 'https://arxiv.org/abs/2401.01234',
  summary: 'A multi-agent system can reduce latency on complex tasks by executing work concurrently.',
  relevance_score: 8, category: ['ai', 'papers'], created_at: '2026-10-08T08:00:00',
}
const summary = `## 阅读依据
这是用于界面验证的示例结果，并非该论文的真实分析。仅摘要，实验未核实。

## 一句话贡献
在给定条件下减少多智能体协作中的通信开销。

## 为什么有效
让工作单元独立推进任务，减少对中心调度器的等待。

## 假设与适用边界
任务需要能够拆分；强依赖任务的收益尚未验证。

## 证据与实验审视
| 检查项 | 阅读结果 |
| --- | --- |
| 基线与指标 | 摘要未提供，待核实 |
| 失败案例 | 未读取实验章节 |

## 何时会失效
高度耦合的任务可能增加通信成本，这是待验证的推断。

## 与已有工作的联系
可与中心化任务调度进行对比；尚未核查相关工作。

## 是否值得采用
先在可拆分的小任务上验证吞吐、正确率与通信成本。`

test('paper modal supports loading, reopening, retry, keyboard, and narrow screens', async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PAPER_READ_BROWSER || 'chrome' })
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
    page.on('pageerror', error => console.error('Browser error:', error.message))
    await page.route('https://fonts.googleapis.com/**', route => route.abort())
    let requests = 0
    let fail = false
    await page.route('**/api/**', async route => {
      const path = new URL(route.request().url()).pathname
      let payload = {}
      let status = 200
      if (path === '/api/content/paper-quick-read') {
        requests += 1
        assert.deepEqual(route.request().postDataJSON(), { item_id: paper.id })
        await new Promise(resolve => setTimeout(resolve, 300))
        status = fail ? 502 : 200
        payload = fail ? { detail: '论文速读生成失败，请重试。' } : { summary, cached: false }
      } else if (path === '/api/briefing/2026-10-08') {
        payload = { items: [paper, { ...paper, id: 'news-test', title: 'Ordinary news', source_type: 'news' }] }
      } else if (path === '/api/dates') {
        payload = { dates: ['2026-10-08'] }
      }
      await route.fulfill({ status, json: payload })
    })
    await page.goto(`${baseURL}/briefing/2026-10-08`, { waitUntil: 'domcontentloaded' })
    const open = page.getByRole('button', { name: '论文速读', exact: true })
    try {
      await open.waitFor({ timeout: 15000 })
    } catch (error) {
      console.error('Rendered page:', await page.locator('body').innerText())
      console.error('Paper button:', await page.locator('.paper-read-button').evaluateAll(elements => elements.map(element => ({ html: element.outerHTML, rect: element.getBoundingClientRect().toJSON(), visibility: getComputedStyle(element).visibility, display: getComputedStyle(element).display }))))
      console.error('Accessibility:', await page.locator('article').first().ariaSnapshot())
      throw error
    }
    assert.equal(await open.count(), 1, 'News must not have a paper-reading button')
    await open.click()
    const dialog = page.getByRole('dialog', { name: '论文速读', exact: true })
    await dialog.getByRole('status').waitFor()
    await page.keyboard.press('Escape')
    await dialog.waitFor({ state: 'hidden' })
    await open.click()
    await dialog.getByRole('heading', { name: '一句话贡献' }).waitFor()
    assert.equal(requests, 1, 'Reopening during generation must not generate twice')
    await page.keyboard.press('Escape')
    assert.equal(await open.evaluate(element => element === document.activeElement), true)
    await open.click()
    assert.equal(requests, 1, 'Reopening a result must reuse it')
    // Tab stays inside the native modal dialog.
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Tab')
      assert.equal(await dialog.evaluate(element => element.contains(document.activeElement) || document.activeElement === document.body), true)
    }
    const screenshots = process.env.PAPER_READ_SCREENSHOTS
    if (screenshots) {
      mkdirSync(screenshots, { recursive: true })
      await page.screenshot({ path: `${screenshots}/desktop.png` })
    }
    await page.setViewportSize({ width: 390, height: 844 })
    const bounds = await dialog.boundingBox()
    assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= 390, 'Dialog must fit a narrow screen')
    assert.equal(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth), true)
    if (screenshots) await page.screenshot({ path: `${screenshots}/mobile.png` })
    await dialog.getByRole('button', { name: '关闭论文速读' }).click()
    await dialog.waitFor({ state: 'hidden' })

    // A fresh page exercises the failure and retry path, not the local result.
    fail = true
    await page.reload()
    await open.click()
    await dialog.getByRole('alert').waitFor()
    assert.match(await dialog.getByRole('alert').textContent(), /生成失败/)
    fail = false
    await dialog.getByRole('button', { name: '重新生成' }).click()
    await dialog.getByRole('heading', { name: '一句话贡献' }).waitFor()
    assert.equal(requests, 3)
  } finally {
    await browser.close()
  }
})
