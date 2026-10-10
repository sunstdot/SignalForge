import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildDailyOpportunityPost,
  getTopOpportunities,
} from './dailyContent.js'

const business = [
  {
    opportunity_title: 'AI代码质检',
    core_insight: 'AI生成代码需要质量兜底。',
    product_form: '帮助前端团队审查 React 代码的插件。',
    source_title: 'react-doctor',
    total_score: 16,
  },
]

const rdev = {
  solutions: [
    {
      title: '需求评审助手',
      trigger: '从 PRD 中发现风险点',
      ai_solution: '自动拆解需求并生成测试点。',
      source_title: 'Agent workflow',
      total_score: 8,
    },
  ],
}

test('getTopOpportunities combines business and rdev opportunities by normalized score', () => {
  assert.deepEqual(
    getTopOpportunities(business, rdev, 2).map(item => item.title),
    ['AI代码质检', '需求评审助手'],
  )
})

test('getTopOpportunities treats empty rdev object as no opportunities', () => {
  assert.deepEqual(
    getTopOpportunities(business, {}, 2).map(item => item.title),
    ['AI代码质检'],
  )
})

test('buildDailyOpportunityPost includes business and rdev sections', () => {
  const post = buildDailyOpportunityPost({ date: '2026-05-12', business, rdev })

  assert.equal(post.title, '今天从 100 条 AI 情报里，挖到 3 个机会')
  assert.match(post.body, /商业机会/)
  assert.match(post.body, /研发机会/)
  assert.match(post.body, /AI代码质检/)
  assert.match(post.body, /需求评审助手/)
})
