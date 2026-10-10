import assert from 'node:assert/strict'
import test from 'node:test'

import { buildFundingInsight, formatWatchValue } from './ventureRadarText.js'

test('formatWatchValue renders priority action rationale objects as text', () => {
  const value = formatWatchValue({
    priority: 'high',
    action: 'Cross-check funding amount',
    rationale: 'Official confirmation is still missing',
  })

  assert.equal(value, '行动：Cross-check funding amount；理由：Official confirmation is still missing；优先级：high')
})

test('formatWatchValue renders item reason timeframe objects as text', () => {
  const value = formatWatchValue({
    item: 'Databricks IPO timeline',
    reason: '$188B valuation suggests IPO is approaching',
    timeframe: 'next quarter',
  })

  assert.equal(value, '事项：Databricks IPO timeline；理由：$188B valuation suggests IPO is approaching；时间：next quarter')
})

test('buildFundingInsight combines funding with same-company context', () => {
  const insight = buildFundingInsight({
    company_name: 'Syntetica',
    amount: '$30M',
    round_type: 'Early-stage funding',
    announced_date: '2026-07-16',
    investors: ['Ecotechnologies 2 fund'],
    why_it_matters: 'Climate tech continues to attract capital.',
    opportunity_angle: 'AI for materials science is an emerging intersection.',
    evidence_gaps: ['Revenue not disclosed'],
  }, {
    companies: [{
      name: 'Syntetica',
      description: 'Paris-based company developing advanced technology to recycle nylon fibers for the clothing industry.',
      category: 'Climate Tech / Materials Recycling',
      founders: ['Marco Bertone'],
      country: 'France',
      source_urls: ['https://example.com/syntetica'],
    }],
    products: [{
      name: 'Nylon recycling platform',
      company: 'Syntetica',
      product_type: 'materials recycling',
      description: 'Recycles nylon fibers from clothing waste.',
    }],
  })

  assert.deepEqual(insight.companyFacts, [
    { label: '所在地/国家', value: 'France' },
    { label: '创始人', value: 'Marco Bertone' },
    { label: '公司业务', value: 'Paris-based company developing advanced technology to recycle nylon fibers for the clothing industry.' },
    { label: '产品/技术', value: 'Nylon recycling platform - materials recycling - Recycles nylon fibers from clothing waste.' },
    { label: '赛道', value: 'Climate Tech / Materials Recycling' },
  ])
  assert.deepEqual(insight.fundingFacts, [
    { label: '金额', value: '$30M' },
    { label: '轮次', value: 'Early-stage funding' },
    { label: '日期', value: '2026-07-16' },
    { label: '投资方', value: 'Ecotechnologies 2 fund' },
  ])
  assert.equal(insight.attention, 'Climate tech continues to attract capital. AI for materials science is an emerging intersection.')
  assert.deepEqual(insight.evidenceGaps, ['Revenue not disclosed'])
})

test('buildFundingInsight marks missing company context as pending verification', () => {
  const insight = buildFundingInsight({
    company_name: 'UnknownCo',
    amount: '$10M',
    officially_confirmed: false,
  }, { companies: [], products: [] })

  assert.deepEqual(insight.companyFacts.slice(0, 4), [
    { label: '所在地/国家', value: '待核验' },
    { label: '创始人', value: '待核验' },
    { label: '公司业务', value: '待核验' },
    { label: '产品/技术', value: '待核验' },
  ])
  assert.deepEqual(insight.fundingFacts, [
    { label: '金额', value: '$10M' },
    { label: '官方确认', value: '否' },
  ])
})

test('buildFundingInsight extracts explicit based-location text from company descriptions', () => {
  const insight = buildFundingInsight({
    company_name: 'Syntetica',
    amount: '$30M',
  }, {
    companies: [{
      name: 'Syntetica',
      description: 'Paris-based company developing advanced technology to recycle nylon fibers.',
    }],
    products: [],
  })

  assert.equal(insight.companyFacts[0].value, 'Paris-based')
})

test('buildFundingInsight prefers a complete Chinese title and hides empty facts', () => {
  const insight = buildFundingInsight({
    entity_type: 'funding_event',
    title: 'Acme AI raises a Series A',
    title_zh: 'Acme AI 宣布完成 A 轮融资',
    pipeline_stage: 'verified',
    event_status: { value: 'announced' },
    amount_raised: { value: null },
    valuation: { value: '$200M' },
    round: { value: 'Series A' },
    announced_date: { value: null },
    lead_investors: { value: [] },
    officially_confirmed: true,
    source_urls: ['https://acme.ai/news/series-a'],
  })

  assert.equal(insight.title, 'Acme AI 宣布完成 A 轮融资')
  assert.deepEqual(insight.visibleFacts, [
    { label: '估值', value: '$200M' },
    { label: '轮次', value: 'Series A' },
    { label: '官方确认', value: '是' },
  ])
  assert.deepEqual(insight.sources, ['https://acme.ai/news/series-a'])
})
