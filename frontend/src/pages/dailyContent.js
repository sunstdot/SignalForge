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

function toArray(value) {
  return Array.isArray(value) ? value : []
}
