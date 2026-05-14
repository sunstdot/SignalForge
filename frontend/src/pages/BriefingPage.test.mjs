import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./BriefingPage.jsx', import.meta.url), 'utf8')

test('BriefingPage does not include the category digest overview feature', () => {
  assert.doesNotMatch(source, /今日 AI 情报速览/)
  assert.doesNotMatch(source, /CategoryDigest/)
  assert.doesNotMatch(source, /category-digest/)
})
