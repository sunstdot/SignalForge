import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { getSignalItems } from './dailySignalData.js'

const page = readFileSync(new URL('./BriefingPage.jsx', import.meta.url), 'utf8')

test('daily signal view uses separate inspiration/execution tracks and keeps all-content entry', () => {
  const briefing = { signals: {
    inspiration: [{ id: 'x1', title: 'Product inspiration' }],
    execution: [{ id: 'p1', title: 'New paper' }], total: 2,
  }, items: [{ id: 'x1' }, { id: 'p1' }] }
  assert.deepEqual(getSignalItems(briefing, 'inspiration').map(item => item.id), ['x1'])
  assert.deepEqual(getSignalItems(briefing, 'execution').map(item => item.id), ['p1'])
  assert.deepEqual(getSignalItems({}, 'execution'), [])
  assert.match(page, /setActiveCategory\] = useState\('signals'\)/)
  assert.match(page, /getSignalItems\(briefing, activeSignalTrack\)/)
  assert.match(page, /setActiveCategory\(briefingData\?\.signals \? 'signals' : 'all'\)/)
  assert.match(page, /今日信号/)
  assert.match(page, /全部内容/)
  assert.match(page, /activeCategory === 'blog'\) return type === 'blog' \|\| type === 'anthropic_blog'/)
})
