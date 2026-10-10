const WATCH_FIELD_LABELS = {
  item: '事项',
  action: '行动',
  reason: '理由',
  rationale: '理由',
  timeframe: '时间',
  priority: '优先级',
}

const WATCH_FIELD_ORDER = ['item', 'action', 'reason', 'rationale', 'timeframe', 'priority']
const PENDING = '待核验'

function normalizeText(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return value.map(normalizeText).filter(Boolean).join('、')
  if (typeof value !== 'object') return String(value)

  const orderedKeys = [
    ...WATCH_FIELD_ORDER.filter(key => Object.prototype.hasOwnProperty.call(value, key)),
    ...Object.keys(value).filter(key => !WATCH_FIELD_ORDER.includes(key)),
  ]

  return orderedKeys
    .map(key => {
      const text = normalizeText(value[key])
      if (!text) return ''
      return `${WATCH_FIELD_LABELS[key] || key}：${text}`
    })
    .filter(Boolean)
    .join('；')
}

export function formatWatchValue(value) {
  return normalizeText(value) || '未命名跟踪项'
}

function stripHtml(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim()
}

function cleanValue(value) {
  const text = stripHtml(normalizeText(value))
  if (!text || /^not disclosed$/i.test(text) || /^unknown$/i.test(text)) return ''
  return text
}

function listValues(value) {
  if (!value) return []
  if (Array.isArray(value)) return value.map(cleanValue).filter(Boolean)
  const text = cleanValue(value)
  return text ? [text] : []
}

function companyName(value) {
  return cleanValue(value?.company_name || value?.company || value?.name || value?.title).toLowerCase()
}

function findCompanyContext(funding, report = {}) {
  const name = companyName(funding)
  if (!name) return null
  return (report.companies || []).find(item => companyName(item) === name) || null
}

function findProductContext(funding, report = {}) {
  const name = companyName(funding)
  if (!name) return null
  return (report.products || []).find(item => companyName(item) === name) || null
}

function fact(label, value) {
  return { label, value: cleanValue(value) || PENDING }
}

function productSummary(product, company) {
  const parts = [
    cleanValue(product?.name),
    cleanValue(product?.product_type),
    cleanValue(product?.description || product?.tagline || product?.what_is_new),
  ].filter(Boolean)
  if (parts.length) return parts.join(' - ')

  const description = cleanValue(company?.description)
  return description
}

function companyLocation(company) {
  const explicitLocation = cleanValue(company?.country || company?.location || company?.headquarters || company?.hq)
  if (explicitLocation) return explicitLocation

  const basedMatch = cleanValue(company?.description).match(/^([A-Z][A-Za-z .'-]+-based)\b/)
  return basedMatch ? basedMatch[1] : ''
}

function founders(company) {
  return cleanValue(company?.founders || company?.founder || company?.founder_names || company?.leadership)
}

export function buildFundingInsight(funding, report = {}) {
  if (funding?.entity_type === 'funding_event' || funding?.amount_raised || funding?.event_status) {
    const fact = (label, field) => {
      const value = fieldValue(field)
      return value ? { label, value } : null
    }
    const visibleFacts = [
      fact('融资金额', funding.amount_raised),
      fact('估值', funding.valuation),
      fact('轮次', funding.round),
      fact('日期', funding.announced_date || funding.closed_date || funding.filed_date),
      fact('领投机构', funding.lead_investors),
      { label: '官方确认', value: funding.officially_confirmed ? '是' : '否' },
    ].filter(Boolean)
    return {
      companyName: cleanValue(funding.company_name) || '相关公司',
      title: cleanValue(funding.title_zh) || cleanValue(funding.title) || cleanValue(funding.what_happened) || '未命名融资信号',
      status: fieldValue(funding.event_status) || 'unclear',
      confidence: cleanValue(funding.confidence) || 'low',
      stage: cleanValue(funding.pipeline_stage) || 'candidate',
      sectorTags: listValues(funding.sector_tags),
      companyProfile: Object.entries(funding.company_profile || {})
        .filter(([, value]) => cleanValue(value))
        .map(([key, value]) => ({
          label: ({ website: '官网', country: '国家/地区', founders: '创始人', business: '公司业务', sector: '赛道', products: '产品' })[key] || key,
          value: cleanValue(value),
        })),
      whatHappened: cleanValue(funding.what_happened) || '当前证据不足，尚不能判断其市场意义。',
      whatChanged: cleanValue(funding.what_changed),
      whyItMatters: cleanValue(funding.why_it_matters),
      marketImplication: cleanValue(funding.market_implication),
      opportunityAngle: cleanValue(funding.opportunity_angle),
      riskAndUncertainty: cleanValue(funding.risk_and_uncertainty),
      nextWatchItems: listValues(funding.next_watch_items),
      visibleFacts,
      evidenceGaps: listValues(funding.evidence_gaps),
      evidenceConflicts: listValues(funding.evidence_conflicts),
      sources: listValues(funding.source_urls),
      evidenceStatus: {
        sourceCount: Number(funding.source_count || 0),
        officialSourceCount: Number(funding.official_source_count || 0),
        independentSourceCount: Number(funding.independent_source_count || 0),
        evidenceScore: Number(funding.evidence_score || 0),
        completenessScore: Number(funding.completeness_score || 0),
      },
      scores: {
        novelty: Number(funding.novelty_score || 0),
        relevance: Number(funding.relevance_score || 0),
        actionability: Number(funding.actionability_score || 0),
        overall: Number(funding.overall_signal_score || 0),
      },
    }
  }

  const company = findCompanyContext(funding, report)
  const product = findProductContext(funding, report)
  const companyDescription = cleanValue(company?.description || funding?.company_description || funding?.description)
  const sector = cleanValue(company?.category || company?.sector || company?.industry || funding?.category || funding?.sector)
  const investors = listValues(funding?.investors)
  const evidenceGaps = [
    ...listValues(company?.evidence_gaps),
    ...listValues(product?.evidence_gaps),
    ...listValues(funding?.evidence_gaps),
  ]
  const attention = [
    cleanValue(company?.why_it_matters || funding?.why_it_matters),
    cleanValue(company?.opportunity_angle || funding?.opportunity_angle),
  ].filter(Boolean).join(' ')

  const fundingFacts = [
    fact('金额', funding?.amount),
    fact('轮次', funding?.round_type || funding?.round),
    fact('日期', funding?.announced_date),
    investors.length ? { label: '投资方', value: investors.join('、') } : null,
    funding?.officially_confirmed === undefined ? null : { label: '官方确认', value: funding.officially_confirmed ? '是' : '否' },
  ].filter(item => item && item.value !== PENDING)

  return {
    companyName: cleanValue(funding?.company_name || funding?.company || company?.name) || '相关公司',
    companyFacts: [
      fact('所在地/国家', companyLocation(company)),
      fact('创始人', founders(company)),
      fact('公司业务', companyDescription),
      fact('产品/技术', productSummary(product, company)),
      fact('赛道', sector),
    ],
    attention: attention || '需要补充公司背景、产品、客户和市场意义后再判断关注优先级。',
    fundingFacts,
    evidenceGaps,
  }
}

function fieldValue(field) {
  if (!field) return ''
  if (typeof field === 'object' && !Array.isArray(field) && Object.prototype.hasOwnProperty.call(field, 'value')) {
    return cleanValue(field.value)
  }
  return cleanValue(field)
}
