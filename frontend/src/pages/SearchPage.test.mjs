import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./SearchPage.jsx', import.meta.url), 'utf8')

test('SearchPage starts empty and searches via the brief endpoint', () => {
  // no static sample brief — data comes from the backend
  assert.doesNotMatch(source, /searchBriefData/)
  assert.match(source, /\/api\/search\/brief/)
  // async job + polling
  assert.match(source, /\/api\/search\/brief\/\$\{jid\}/)
  assert.match(source, /status === 'idle'/)
  assert.match(source, /status === 'running'/)
})

test('SearchPage renders the brief dashboard sections when done', () => {
  assert.match(source, /status === 'done' && brief/)
  for (const sec of ['综合简报', '关键模式', '让我深入', '情报时间线']) {
    assert.match(source, new RegExp(sec))
  }
  for (const panel of ['概览', '平台分布', 'Top Voices', '数据缺口说明']) {
    assert.match(source, new RegExp(panel))
  }
})

test('SearchPage supports all six platforms and guards unknown ones', () => {
  for (const p of ['reddit', 'youtube', 'tiktok', 'instagram']) {
    assert.match(source, new RegExp(`${p}:`))
  }
  assert.match(source, /const PF = /)  // safe platform accessor
})
