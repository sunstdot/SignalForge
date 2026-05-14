import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildDailyBriefingPost,
  buildDailyOpportunityPost,
  getTopBriefingItems,
  getTopOpportunities,
} from './dailyContent.js'

const briefing = {
  date: '2026-05-12',
  items: [
    { id: 'a', title: 'ModelLens', source: 'HuggingFace Papers', source_type: 'paper', summary: '模型选择变得复杂。', relevance_score: 8 },
    { id: 'b', title: 'react-doctor', source: 'GitHub Trending', source_type: 'repo', summary: '检查 AI 生成 React 代码。', relevance_score: 9 },
    { id: 'c', title: 'privacy-filter', source: 'HuggingFace Models', source_type: 'model', summary: '识别隐私信息。', relevance_score: 7 },
    { id: 'd', title: 'AI shopping', source: 'News', source_type: 'news', summary: '对话式购物。', relevance_score: 6 },
  ],
}

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

test('getTopBriefingItems sorts by relevance and limits count', () => {
  assert.deepEqual(
    getTopBriefingItems(briefing, 3).map(item => item.title),
    ['react-doctor', 'ModelLens', 'privacy-filter'],
  )
})

test('getTopBriefingItems diversifies sources when one category dominates', () => {
  const paperHeavyBriefing = {
    items: [
      { id: 'p1', title: 'Paper 1', source_type: 'paper', relevance_score: 9 },
      { id: 'p2', title: 'Paper 2', source_type: 'paper', relevance_score: 9 },
      { id: 'p3', title: 'Paper 3', source_type: 'paper', relevance_score: 9 },
      { id: 'p4', title: 'Paper 4', source_type: 'paper', relevance_score: 9 },
      { id: 'p5', title: 'Paper 5', source_type: 'paper', relevance_score: 9 },
      { id: 'r1', title: 'Repo 1', source_type: 'repo', relevance_score: 8 },
      { id: 'm1', title: 'Model 1', source_type: 'model', relevance_score: 8 },
      { id: 'n1', title: 'News 1', source_type: 'news', relevance_score: 8 },
    ],
  }

  assert.deepEqual(
    getTopBriefingItems(paperHeavyBriefing, 5).map(item => item.title),
    ['Paper 1', 'Repo 1', 'Model 1', 'News 1', 'Paper 2'],
  )
})

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

test('buildDailyBriefingPost returns a stable xiaohongshu structure', () => {
  const post = buildDailyBriefingPost(briefing)

  assert.equal(post.title, '今天 AI 圈最值得看的 5 条情报')
  assert.match(post.body, /1\. react-doctor/)
  assert.match(post.body, /我的判断：/)
  assert.match(post.tags, /#AI情报/)
})

test('buildDailyOpportunityPost includes business and rdev sections', () => {
  const post = buildDailyOpportunityPost({ date: '2026-05-12', business, rdev })

  assert.equal(post.title, '今天从 100 条 AI 情报里，挖到 3 个机会')
  assert.match(post.body, /商业机会/)
  assert.match(post.body, /研发机会/)
  assert.match(post.body, /AI代码质检/)
  assert.match(post.body, /需求评审助手/)
})
