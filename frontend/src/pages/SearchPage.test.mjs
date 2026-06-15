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

test('SearchPage triggers last30days research when local search is empty', () => {
  // calls the research API
  assert.match(source, /\/api\/last30days\/research/)
  // only triggers when local has no results but a keyword is present
  assert.match(source, /filtered\.length === 0 && q\.trim\(\)/)
  // polls job status and surfaces a researching state
  assert.match(source, /setResearching\(true\)/)
  assert.match(source, /researchError/)
})
