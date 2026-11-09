import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { getSignalItems, getEventItems, getAccountItems } from './dailySignalData.js'

const page = readFileSync(new URL('./BriefingPage.jsx', import.meta.url), 'utf8')

test('account groups preserve handle coverage and legacy snapshots stay empty', () => {
  const group = { handle: '@dotey', status: 'partial', posts: [{ id: 'x-1', kind: 'quote' }] }
  assert.deepEqual(getAccountItems({ signals: { accounts: [group] } }), [group])
  assert.deepEqual(getAccountItems({ signals: { inspiration: [{ id: 'old' }] } }), [])
  assert.deepEqual(getAccountItems(null), [])
  assert.deepEqual(getAccountItems({ signals: { accounts: [{ handle: '@oran_ge', status: 'partial' }, null] } }),
    [{ handle: '@oran_ge', status: 'partial', posts: [] }])
})

test('event items come from cached radar and old snapshots stay empty', () => {
  assert.deepEqual(getEventItems({ signals: { events: [{ id: 'event-1' }] } }), [{ id: 'event-1' }])
  assert.deepEqual(getEventItems({ signals: { inspiration: [{ id: 'old' }] } }), [])
  assert.deepEqual(getEventItems(null), [])
})

test('daily signal view shows a curated list and keeps all-content entry', () => {
  const briefing = { signals: {
    inspiration: [{ id: 'x1', title: 'Product inspiration' }],
    execution: [{ id: 'p1', title: 'New paper' }], total: 2,
  }, items: [{ id: 'x1' }, { id: 'p1' }] }
  assert.deepEqual(getSignalItems(briefing, 'inspiration').map(item => item.id), ['x1'])
  assert.deepEqual(getSignalItems(briefing, 'execution').map(item => item.id), ['p1'])
  assert.deepEqual(getSignalItems({}, 'execution'), [])
  assert.match(page, /setActiveCategory\] = useState\('signals'\)/)
  assert.match(page, /setActiveCategory\(briefingData\?\.signals \? 'signals' : 'all'\)/)
  assert.match(page, /今日信号/)
  assert.match(page, /全部内容/)
  assert.match(page, /SignalCard/)
  assert.match(page, /SignalLearningPanel/)
  assert.match(page, /activeCategory === 'blog'\) return type === 'blog' \|\| type === 'anthropic_blog'/)
})
