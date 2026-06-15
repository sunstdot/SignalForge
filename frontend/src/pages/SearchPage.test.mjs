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

test('SearchPage triggers last30days research directly on every search', () => {
  // calls the research API
  assert.match(source, /\/api\/last30days\/research/)
  // search goes straight to research (no local-first gating)
  assert.doesNotMatch(source, /filtered\.length === 0 && q\.trim\(\)/)
  // doSearch runs research for the keyword directly
  assert.match(source, /runResearch\(topic, st, token\)/)
  // polls job status and surfaces a researching state
  assert.match(source, /setResearching\(true\)/)
  assert.match(source, /researchError/)
})

test('SearchPage only shows last30days-origin results', () => {
  assert.match(source, /metadata\?\.origin !== 'last30days'/)
})

test('SearchPage limits filter chips to the six social platforms', () => {
  assert.match(source, /const L30_TYPES = \['reddit', 'x', 'hn', 'youtube', 'tiktok', 'instagram'\]/)
})
