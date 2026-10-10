import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./Sidebar.jsx', import.meta.url), 'utf8')

test('Sidebar uses weekly venture radar archives on venture routes', () => {
  assert.match(source, /\/api\/venture-radar\/weeks/)
  assert.match(source, /\/venture-radar\/week\/\$\{/)
  assert.match(source, /ventureWeekMatch/)
})

test('Sidebar keeps daily archives for non-venture pages', () => {
  assert.match(source, /\/api\/dates/)
  assert.match(source, /\/briefing\/\$\{d\.date\}/)
})

test('Sidebar uses populated opportunity dates on daily opportunity routes', () => {
  assert.match(source, /fetch\('\/api\/dates\/opportunities'\)/)
  assert.match(source, /latestOpportunityDate/)
  assert.match(source, /isDailyOpportunity \? opportunityDates : dates/)
  assert.match(source, /\/daily-opportunities\/\$\{latestOpportunityDate\}/)
})
