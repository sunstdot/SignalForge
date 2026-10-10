import assert from 'node:assert/strict'
import test from 'node:test'

import { buildIdeaPayloadFromOpportunity } from './opportunityIdeaPayload.js'

const businessOpportunity = {
  kind: 'business',
  title: 'LLM Token Saver',
  trigger: '开源工具已证明可无损压缩上下文 60-95%。',
  scenario: '帮助使用 GPT 等 LLM 的开发者自动压缩上下文。',
  solution: '免费额度 + 按节省 token 量订阅。',
  features: ['MCP 集成', '云端 API 代理'],
  resistance: '开发者需要信任代理服务。',
  audience: ['独立开发者', '中小团队'],
  totalScore: 19,
  source: 'GitHub Trending',
  sourceTitle: 'Token Saver Repo',
  sourceUrl: 'https://example.com/token-saver',
}

test('buildIdeaPayloadFromOpportunity maps a business opportunity to an idea payload', () => {
  const payload = buildIdeaPayloadFromOpportunity(businessOpportunity, '2026-06-04')

  assert.equal(payload.title, 'LLM Token Saver')
  assert.equal(payload.difficulty, 'medium')
  assert.equal(payload.estimated_days, 7)
  assert.equal(payload.status, 'pending')
  assert.equal(payload.priority, 19)
  assert.equal(payload.briefing_date, '2026-06-04')
  assert.equal(payload.source_type, 'opportunity')
  assert.equal(payload.source_title, 'Token Saver Repo')
  assert.equal(payload.source_url, 'https://example.com/token-saver')
  assert.deepEqual(payload.tags, ['商业机会', '独立开发者', '中小团队'])
})

test('buildIdeaPayloadFromOpportunity includes opportunity details in markdown description', () => {
  const payload = buildIdeaPayloadFromOpportunity(businessOpportunity, '2026-06-04')

  assert.match(payload.description, /\*\*核心洞察\*\*/)
  assert.match(payload.description, /无损压缩上下文/)
  assert.match(payload.description, /\*\*应用场景\*\*/)
  assert.match(payload.description, /自动压缩上下文/)
  assert.match(payload.description, /\*\*商业模式\*\*/)
  assert.match(payload.description, /按节省 token/)
  assert.match(payload.description, /\*\*MVP 功能\*\*/)
  assert.match(payload.description, /- MCP 集成/)
  assert.match(payload.description, /\*\*潜在风险\*\*/)
  assert.match(payload.description, /信任代理服务/)
})

test('buildIdeaPayloadFromOpportunity rejects non-business opportunities', () => {
  assert.equal(
    buildIdeaPayloadFromOpportunity({ kind: 'rdev', title: '需求评审助手' }, '2026-06-04'),
    null,
  )
})
