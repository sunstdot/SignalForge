import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./SearchPage.jsx', import.meta.url), 'utf8')
const briefData = readFileSync(new URL('./searchBriefData.js', import.meta.url), 'utf8')

test('SearchPage renders the synthesized intelligence brief', () => {
  assert.match(source, /import \{ SAMPLE_BRIEF \} from '\.\/searchBriefData'/)
  // the four numbered sections of the brief dashboard
  for (const sec of ['综合简报', '关键模式', '让我深入', '情报时间线']) {
    assert.match(source, new RegExp(sec))
  }
})

test('SearchPage renders the right-rail panels', () => {
  for (const panel of ['概览', '平台分布', 'Top Voices', '数据缺口说明']) {
    assert.match(source, new RegExp(panel))
  }
})

test('SearchPage has timeline platform filters and featured toggle', () => {
  assert.match(source, /setPlat/)
  assert.match(source, /featOnly/)
  assert.match(source, /仅看精选/)
})

test('searchBriefData exposes the brief shape', () => {
  assert.match(briefData, /export const SAMPLE_BRIEF/)
  for (const key of ['themes', 'patterns', 'deepDive', 'dashboard', 'voices', 'timeline']) {
    assert.match(briefData, new RegExp(`${key}:`))
  }
})
