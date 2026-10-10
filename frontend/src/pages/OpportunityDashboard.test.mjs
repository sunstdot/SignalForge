import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./OpportunityDashboard.jsx', import.meta.url), 'utf8')

test('OpportunityDashboard imports the opportunity idea payload builder', () => {
  assert.match(source, /buildIdeaPayloadFromOpportunity/)
})

test('OpportunityCard has a separate idea pool action from the share checkbox', () => {
  assert.match(source, /onSaveIdea/)
  assert.match(source, /加入想法池/)
  assert.match(source, /已加入想法池/)
})
