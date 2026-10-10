function normalizeTags(audience = []) {
  return ['商业机会', ...audience.filter(Boolean)]
}

function buildDescription(item) {
  return [
    item.trigger && `**核心洞察**\n${item.trigger}`,
    item.scenario && `**应用场景**\n${item.scenario}`,
    item.solution && `**商业模式**\n${item.solution}`,
    item.features?.length > 0 && `**MVP 功能**\n${item.features.map(feature => `- ${feature}`).join('\n')}`,
    item.resistance && `**潜在风险**\n${item.resistance}`,
  ].filter(Boolean).join('\n\n')
}

export function buildIdeaPayloadFromOpportunity(item, date) {
  if (!item || item.kind !== 'business') return null

  return {
    title: item.title || '未命名商业机会',
    description: buildDescription(item),
    difficulty: 'medium',
    estimated_days: 7,
    tags: normalizeTags(item.audience),
    status: 'pending',
    priority: item.totalScore || 0,
    briefing_date: date,
    source_type: 'opportunity',
    source_title: item.sourceTitle || item.source || '',
    source_url: item.sourceUrl || '',
  }
}
