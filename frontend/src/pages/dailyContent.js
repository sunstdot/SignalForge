const SOURCE_LABELS = {
  arxiv: '论文',
  paper: '论文',
  repo: 'GitHub',
  github: 'GitHub',
  model: '模型',
  rss: '资讯',
  news: '资讯',
  blog: '官方博客',
  wechat: '公众号',
  investor: '投资者',
  smolai: 'AI资讯',
  hackernews: '技术资讯',
}

export function getTopBriefingItems(briefing, limit = 5) {
  const ranked = [...(briefing?.items || [])]
    .sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
  const selected = []
  const selectedIds = new Set()
  const selectedTypes = new Set()

  if (ranked[0]) {
    selected.push(ranked[0])
    selectedIds.add(ranked[0].id)
    selectedTypes.add(getBriefingType(ranked[0]))
  }

  for (const item of ranked) {
    const type = getBriefingType(item)
    if (selectedIds.has(item.id) || selectedTypes.has(type)) continue
    selected.push(item)
    selectedIds.add(item.id)
    selectedTypes.add(type)
    if (selected.length >= limit) return selected
  }

  for (const item of ranked) {
    if (selectedIds.has(item.id)) continue
    selected.push(item)
    selectedIds.add(item.id)
    if (selected.length >= limit) break
  }

  return selected
}

export function normalizeBusinessOpportunity(item) {
  return {
    kind: 'business',
    title: item.opportunity_title || item.title || '未命名商业机会',
    sourceTitle: item.source_title || item.sourceTitle || '',
    insight: item.core_insight || item.trigger || '',
    form: item.product_form || item.scenario || '',
    action: item.mvp_features?.length ? item.mvp_features.join('、') : item.business_model || '',
    score: item.total_score || 0,
    scoreMax: 20,
  }
}

export function normalizeRdevOpportunity(item) {
  return {
    kind: 'rdev',
    title: item.title || '未命名研发机会',
    sourceTitle: item.source_title || item.sourceTitle || item.source_item_title || '',
    insight: item.trigger || item.scenario || '',
    form: item.ai_solution || item.solution || '',
    action: item.implementation || item.impact || '',
    score: item.total_score || item.scores?.overall || 0,
    scoreMax: 10,
  }
}

export function getTopOpportunities(business = [], rdev = {}, limit = 6) {
  const businessItems = toArray(business).map(normalizeBusinessOpportunity)
  const rdevItems = toArray(rdev?.solutions ?? rdev).map(normalizeRdevOpportunity)

  return [...businessItems, ...rdevItems]
    .sort((a, b) => (b.score / b.scoreMax) - (a.score / a.scoreMax))
    .slice(0, limit)
}

export function buildDailyBriefingPost(briefing) {
  const items = getTopBriefingItems(briefing, 5)
  const lines = [
    '今天我从论文、GitHub、模型和资讯里筛了几条值得看的 AI 情报：',
    '',
    ...items.flatMap((item, index) => [
      `${index + 1}. ${item.title}`,
      `来源：${SOURCE_LABELS[item.source_type] || item.source || 'AI情报'}`,
      `说明了什么：${compactText(item.summary, 72) || '这个信号值得继续跟踪。'}`,
      '',
    ]),
    '我的判断：',
    buildBriefingJudgement(items),
  ]

  return {
    title: '今天 AI 圈最值得看的 5 条情报',
    body: lines.join('\n').trim(),
    tags: '#AI情报 #AI产品 #AI创业 #技术趋势 #开源项目 #程序员日常',
  }
}

export function buildDailyOpportunityPost({ business = [], rdev = {} }) {
  const businessTop = toArray(business).map(normalizeBusinessOpportunity).slice(0, 3)
  const rdevTop = toArray(rdev?.solutions).map(normalizeRdevOpportunity).slice(0, 3)
  const selected = [...businessTop, ...rdevTop].slice(0, 3)

  const lines = [
    '今天我用自己的 AI 情报工具扫了一遍论文、GitHub、模型和资讯，发现几个比较值得关注的机会：',
    '',
    ...selected.flatMap((item, index) => [
      `${index + 1}. ${item.kind === 'business' ? '商业机会' : '研发机会'}：${item.title}`,
      item.sourceTitle ? `来源情报：${item.sourceTitle}` : '',
      `趋势判断：${item.insight || '这个方向正在出现新的可用能力。'}`,
      `可以怎么做：${item.form || item.action || '先做一个轻量 MVP 验证需求。'}`,
      '',
    ]).filter(Boolean),
    '我的判断：',
    '这类机会不一定适合大公司立刻重投入，但很适合独立开发者或小团队先做轻量产品验证。',
  ]

  return {
    title: '今天从 100 条 AI 情报里，挖到 3 个机会',
    body: lines.join('\n').trim(),
    tags: '#AI情报机会 #AI创业 #独立开发 #AI产品 #研发提效 #开源项目',
  }
}

function buildBriefingJudgement(items) {
  const types = new Set(items.map(item => item.source_type))
  if (types.has('repo') || types.has('github')) {
    return '今天的信号里，开源项目和工程工具仍然最容易转化成可落地产品，适合先从小工具或插件切入。'
  }
  if (types.has('paper') || types.has('arxiv')) {
    return '今天的信号更偏技术能力变化，短期重点不是直接商业化，而是观察哪些能力能被产品化封装。'
  }
  return '今天的信息重点在应用扩散和市场变化，值得继续观察哪些场景会先出现明确付费需求。'
}

function compactText(text = '', maxLength = 80) {
  const clean = String(text).replace(/\s+/g, ' ').trim()
  if (clean.length <= maxLength) return clean
  return `${clean.slice(0, maxLength - 1)}...`
}

function toArray(value) {
  return Array.isArray(value) ? value : []
}

function getBriefingType(item) {
  if (item?.source_type === 'hackernews' || item?.source === 'HackerNews Daily') return 'hackernews'
  return item?.source_type || 'news'
}
