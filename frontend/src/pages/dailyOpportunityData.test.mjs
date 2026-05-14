import assert from 'node:assert/strict'
import test from 'node:test'

import { loadDailyOpportunityData } from './dailyOpportunityData.js'

test('loadDailyOpportunityData deduplicates concurrent requests for the same date', async () => {
  const originalFetch = globalThis.fetch
  const requestedUrls = []

  globalThis.fetch = async (url) => {
    requestedUrls.push(url)
    if (url.endsWith('/opportunities')) {
      return {
        ok: true,
        json: async () => ({ opportunities: [{ opportunity_title: 'A' }] }),
      }
    }
    return {
      ok: true,
      json: async () => ({ solutions: [{ title: 'B' }] }),
    }
  }

  try {
    const [first, second] = await Promise.all([
      loadDailyOpportunityData('2026-05-14'),
      loadDailyOpportunityData('2026-05-14'),
    ])

    assert.deepEqual(first, second)
    assert.deepEqual(requestedUrls, [
      '/api/briefing/2026-05-14/opportunities',
      '/api/briefing/2026-05-14/rdev-opportunities',
    ])
  } finally {
    globalThis.fetch = originalFetch
  }
})
