import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./SearchPage.jsx', import.meta.url), 'utf8')

test('SearchPage exposes last30days social source types', () => {
  for (const label of ['Reddit', 'YouTube', 'TikTok', 'Instagram', 'Hacker News']) {
    assert.match(source, new RegExp(label))
  }
  for (const key of ['reddit:', 'youtube:', 'tiktok:', 'instagram:', 'hn:']) {
    assert.match(source, new RegExp(key))
  }
})
