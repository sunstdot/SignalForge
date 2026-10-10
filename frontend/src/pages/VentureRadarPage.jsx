import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { buildFundingInsight, formatWatchValue } from './ventureRadarText'

const STAGE_TABS = [
  { key: 'verified', label: '已验证情报', icon: '✓' },
  { key: 'watchlist', label: '待验证信号', icon: '!' },
  { key: 'candidate', label: '候选池', icon: '?' },
]

const VERIFIED_TYPE_FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'funding', label: '融资' },
  { key: 'product', label: '产品' },
]

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

function shortText(value, max = 260) {
  const text = stripHtml(value)
  return text.length > max ? `${text.slice(0, max)}...` : text
}

function confidenceClass(value) {
  return `confidence ${String(value || 'unknown').toLowerCase()}`
}

function sourceErrorCount(report) {
  const errors_by_source = report?.errors_by_source || {}
  return Object.values(errors_by_source).reduce((sum, value) => sum + (Array.isArray(value) ? value.length : 1), 0)
}

function getSourceUrls(item) {
  return listValues(item?.source_urls || item?.source_url)
}

function primarySourceUrl(item) {
  return getSourceUrls(item)[0] || cleanValue(item?.url || item?.website || item?.github_url || item?.producthunt_url || item?.huggingface_url)
}

function listValues(value) {
  if (!value) return []
  if (Array.isArray(value)) return value.filter(Boolean).map(item => typeof item === 'string' ? item : JSON.stringify(item))
  if (typeof value === 'string') return value.trim() ? [value.trim()] : []
  return [JSON.stringify(value)]
}

function cleanValue(value) {
  const text = stripHtml(value)
  if (!text || /^not disclosed$/i.test(text) || /^unknown$/i.test(text)) return ''
  return text
}

function chineseIntro(item, type) {
  if (type === 'funding') {
    const company = cleanValue(item.company_name || item.company || item.name || item.title)
    const amount = cleanValue(item.amount)
    const valuation = cleanValue(item.valuation)
    const round = cleanValue(item.round || item.round_type)
    const date = cleanValue(item.announced_date)
    const parts = []
    if (amount) parts.push(`融资金额 ${amount}`)
    if (valuation) parts.push(`估值 ${valuation}`)
    if (round) parts.push(`轮次 ${round}`)
    if (date) parts.push(`披露日期 ${date}`)
    const status = item.officially_confirmed ? '已有官方确认' : '尚未看到官方确认'
    return `融资信号：${company || '相关公司'}出现融资或估值动态。${parts.length ? parts.join('，') + '。' : ''}${status}，需要继续核验官方公告、领投方和业务进展。`
  }
  if (type === 'product') {
    const name = cleanValue(item.name || item.title)
    const channel = cleanValue(item.launch_channel || item.platform)
    const productType = cleanValue(item.product_type)
    const users = listValues(item.target_users).slice(0, 3).join('、')
    return `产品线索：${name || '该产品'}${channel ? `来自 ${channel}` : ''}${productType ? `，类型为 ${productType}` : ''}${users ? `，主要面向 ${users}` : ''}。可继续观察产品定位、用户反馈、商业化和差异化能力。`
  }
  if (type === 'signal') {
    const signalType = cleanValue(item.signal_type)
    const strength = cleanValue(item.signal_strength)
    const score = item.signal_score ? `，信号分 ${item.signal_score}` : ''
    return `市场信号：这是一条${signalType || '创投/产品'}相关线索${strength ? `，强度为 ${strength}` : ''}${score}。建议结合来源链接继续判断它对 AI 产品机会、融资热度或市场变化的意义。`
  }
  return ''
}

function quickRead(item, type) {
  const intro = chineseIntro(item, type)
  if (type === 'funding') {
    const amount = cleanValue(item.amount)
    const valuation = cleanValue(item.valuation)
    const date = cleanValue(item.announced_date)
    const facts = [
      amount ? `融资金额：${amount}` : '',
      valuation ? `估值：${valuation}` : '',
      date ? `披露日期：${date}` : '',
      item.officially_confirmed ? '官方确认：是' : '官方确认：否',
    ].filter(Boolean)
    return {
      core: intro,
      facts,
      watch: cleanValue(item.why_it_matters || item.opportunity_angle) || '需要继续核验官方公告、领投方、业务进展和同类公司的资本动向。',
    }
  }
  if (type === 'product') {
    const facts = [
      cleanValue(item.launch_channel || item.platform) ? `发布渠道：${cleanValue(item.launch_channel || item.platform)}` : '',
      cleanValue(item.product_type) ? `产品类型：${cleanValue(item.product_type)}` : '',
      ...listValues(item.traction_signals).slice(0, 3),
    ].filter(Boolean)
    return {
      core: intro,
      facts,
      watch: cleanValue(item.why_it_matters || item.opportunity_angle || item.what_is_new) || '重点看产品定位、用户反馈、商业化路径和能否形成差异化工作流。',
    }
  }
  const facts = [
    cleanValue(item.signal_type) ? `信号类型：${cleanValue(item.signal_type)}` : '',
    cleanValue(item.signal_strength) ? `信号强度：${cleanValue(item.signal_strength)}` : '',
    item.signal_score ? `信号分：${item.signal_score}` : '',
  ].filter(Boolean)
  return {
    core: intro,
    facts,
    watch: cleanValue(item.why_it_matters || item.opportunity_angle || item.relevance_to_signalforge) || '建议结合来源、相关公司和同类信号判断是否值得持续跟踪。',
  }
}

function combinedIntelItems(report) {
  return [
    ...(report?.funding_rounds || []).map(item => ({ item, type: 'funding' })),
    ...(report?.products || []).map(item => ({ item, type: 'product' })),
    ...(report?.signals || []).map(item => ({ item, type: 'signal' })),
  ]
}

export default function VentureRadarPage() {
  const { weekId } = useParams()
  const [weekReports, setWeekReports] = useState([])
  const [report, setReport] = useState(null)
  const [activeStage, setActiveStage] = useState('verified')
  const [activeVerifiedType, setActiveVerifiedType] = useState('all')
  const [error, setError] = useState('')

  const loadWeek = useCallback(async (weekId) => {
    const res = await fetch(`/api/venture-radar/weeks/${weekId}`)
    if (!res.ok) throw new Error(`读取周报失败: HTTP ${res.status}`)
    const data = await res.json()
    const aggregate = data.aggregate || {}
    const reports = data.reports || []
    const topics = reports.map(item => item.topic).filter(Boolean)
    const latest = reports[0] || {}
    setWeekReports(reports)
    setReport({
      topic: topics.length ? `${data.week} · ${topics.join(' / ')}` : `${data.week} 创投产品雷达`,
      generated_at: latest.generated_at || '',
      lookback_days: latest.lookback_days || 7,
      mode: 'weekly',
      products: aggregate.products || [],
      funding_rounds: aggregate.funding_rounds || [],
      companies: aggregate.companies || [],
      signals: aggregate.signals || [],
      source_links: aggregate.source_links || [],
      next_watch_items: aggregate.next_watch_items || [],
      research_plan: aggregate.research_plan || [],
      intelligence_events: aggregate.intelligence_events || [],
      intelligence_by_stage: aggregate.intelligence_by_stage || { verified: [], watchlist: [], candidate: [], rejected: [] },
      quality_metrics: aggregate.quality_metrics || {},
      enrichment_tasks: aggregate.enrichment_tasks || [],
      errors_by_source: aggregate.errors_by_source || {},
      source_strategy: {
        websearch_queries: topics,
        notes: `${reports.length} reports aggregated for ${data.week}`,
      },
    })
    setActiveStage('verified')
    setActiveVerifiedType('all')
    return data
  }, [])

  const loadWeeks = useCallback(async () => {
    const res = await fetch('/api/venture-radar/weeks')
    if (!res.ok) throw new Error(`读取周列表失败: HTTP ${res.status}`)
    const data = await res.json()
    const nextWeeks = data.weeks || []
    return nextWeeks
  }, [])

  useEffect(() => {
    let ignore = false
    async function init() {
      try {
        const nextWeeks = await loadWeeks()
        if (ignore) return
        const targetWeek = weekId || nextWeeks[0]?.week
        if (targetWeek) {
          await loadWeek(targetWeek)
        } else {
          setReport(null)
          setWeekReports([])
        }
      } catch (e) {
        if (!ignore) setError(String(e.message || e))
      }
    }
    init()
    return () => {
      ignore = true
    }
  }, [loadWeek, loadWeeks, weekId])

  const isResearchMode = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('research') === '1'
  const stageTabs = useMemo(() => STAGE_TABS.filter(tab => tab.key !== 'candidate' || isResearchMode), [isResearchMode])
  const stageItems = useMemo(() => report?.intelligence_by_stage || { verified: [], watchlist: [], candidate: [] }, [report])
  const filteredStageItems = useMemo(() => {
    const current = stageItems[activeStage] || []
    if (activeStage !== 'verified' || activeVerifiedType === 'all') return current
    return current.filter(entry => inferCardType(entry.item || entry) === activeVerifiedType)
  }, [activeStage, activeVerifiedType, stageItems])
  const qualityMetrics = report?.quality_metrics || {}

  function tabCount(stageKey) {
    return (stageItems?.[stageKey] || []).length
  }

  function verifiedTypeCount(typeKey) {
    const verified = stageItems?.verified || []
    if (typeKey === 'all') return verified.length
    return verified.filter(entry => inferCardType(entry.item || entry) === typeKey).length
  }

  return (
    <div className="venture-page">
      <style>{STYLES}</style>
      <header className="venture-header">
        <div>
          <p className="venture-kicker">Venture Product Radar</p>
          <h1>创投产品雷达</h1>
          <p>{report ? `${report.topic} · ${formatDate(report.generated_at)} · lookback ${report.lookback_days || 7} days · ${report.mode || 'weekly'} mode` : '暂无周归档'}</p>
        </div>
      </header>

      {error && <div className="venture-error">{error}</div>}

      <section className="venture-stats">
        <Stat label="验证率" value={formatPercent(qualityMetrics.verified_ratio)} />
        <Stat label="官方来源覆盖" value={formatPercent(qualityMetrics.official_source_coverage)} />
        <Stat label="平均完整度" value={formatScore(qualityMetrics.average_completeness_score)} />
        <Stat label="重复率" value={formatPercent(qualityMetrics.duplicate_rate)} />
        <Stat label="低置信占比" value={formatPercent(qualityMetrics.low_confidence_ratio)} />
        <Stat label="可行动信号" value={qualityMetrics.actionable_signal_count || 0} />
        <Stat label="待验证" value={qualityMetrics.pending_verification_count || 0} />
      </section>

      <main className="venture-layout">
        <section className="venture-report">
          {!report ? (
            <div className="venture-empty large">暂无归档内容</div>
          ) : (
            <>
              {weekReports.length > 0 && (
                <div className="week-context">
                  <strong>本周获取批次</strong>
                  <div>{weekReports.map(item => <span key={item.id}>{item.topic}</span>)}</div>
                </div>
              )}
              <div className="venture-tabs" role="tablist" aria-label="创投产品雷达情报阶段">
                {stageTabs.map(tab => (
                  <button key={tab.key} type="button" className={activeStage === tab.key ? 'active' : ''} onClick={() => setActiveStage(tab.key)}>
                    <span>{tab.icon}</span>
                    <strong>{tab.label}</strong>
                    <em>{tabCount(tab.key)}</em>
                  </button>
                ))}
              </div>

              {activeStage === 'verified' && (
                <div className="verified-type-tabs" role="tablist" aria-label="已验证情报类型">
                  {VERIFIED_TYPE_FILTERS.map(tab => (
                    <button key={tab.key} type="button" className={activeVerifiedType === tab.key ? 'active' : ''} onClick={() => setActiveVerifiedType(tab.key)}>
                      <strong>{tab.label}</strong>
                      <em>{verifiedTypeCount(tab.key)}</em>
                    </button>
                  ))}
                </div>
              )}

              <CardList items={filteredStageItems} report={report} />
            </>
          )}
        </section>
      </main>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="venture-stat">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
}

function CardList({ items, type, report }) {
  if (!items.length) return <div className="venture-empty">暂无匹配条目</div>
  return (
    <div className="venture-cards">
      {items.map((entry, index) => {
        const item = entry.item || entry
        const cardType = entry.type || type || inferCardType(item)
        return <ReportCard key={`${cardType}-${index}`} item={item} type={cardType} report={report} />
      })}
    </div>
  )
}

function inferCardType(item) {
  if (item.entity_type === 'funding_event') return 'funding'
  if (item.entity_type === 'product_launch') return 'product'
  return 'signal'
}

function ReportCard({ item, type, report }) {
  const insight = type === 'funding' ? buildFundingInsight(item, report) : null
  const title = insight?.title || item.name || item.title || item.company_name || item.company || 'Untitled'
  const body = insight?.whatHappened || chineseIntro(item, type) || item.description || item.market_signal || item.summary || ''
  const evidenceGaps = listValues(item.evidence_gaps)
  const sourceUrl = primarySourceUrl(item)
  const content = (
    <>
      <div className="card-top">
        <span className="type">{typeLabel(type)}</span>
        {item.pipeline_stage && <span className={`stage-pill ${item.pipeline_stage}`}>{stageLabel(item.pipeline_stage)}</span>}
        {insight?.status && <span className="status-pill">{statusLabel(insight.status)}</span>}
        {insight?.sectorTags.map(tag => <span className="sector-pill" key={tag}>{tag}</span>)}
        <span className={confidenceClass(item.confidence)}>{confidenceLabel(item.confidence)}</span>
      </div>
      <h3>{sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer">{title}</a> : title}</h3>
      {type === 'funding' ? <p><strong>发生了什么：</strong>{body}</p> : <p>{body}</p>}
      {type === 'signal' && <Meta values={[item.signal_type, item.signal_strength, item.signal_score ? `score ${item.signal_score}` : '']} />}
      {type === 'funding' ? <FundingInsight insight={insight} /> : <QuickRead item={item} type={type} />}
      {type !== 'funding' && evidenceGaps.length > 0 && <div className="gaps">证据缺口：{evidenceGaps.join('、')}</div>}
    </>
  )
  return <article className="venture-card">{content}</article>
}

function FundingInsight({ insight }) {
  return (
    <div className="funding-intel">
      {insight.visibleFacts.length > 0 && (
        <>
          <div className="quick-read-title">本轮融资</div>
          <div className="funding-facts">
            {insight.visibleFacts.map(fact => <span key={fact.label}>{fact.label}：{fact.value}</span>)}
          </div>
        </>
      )}
      {insight.whatChanged && <p><strong>发生了哪些变化：</strong>{insight.whatChanged}</p>}
      {insight.whyItMatters && <p><strong>为什么值得关注：</strong>{insight.whyItMatters}</p>}
      {insight.marketImplication && <p><strong>市场信号：</strong>{insight.marketImplication}</p>}
      {insight.opportunityAngle && <p><strong>机会角度：</strong>{insight.opportunityAngle}</p>}
      {insight.riskAndUncertainty && <p><strong>风险与不确定性：</strong>{insight.riskAndUncertainty}</p>}
      {insight.companyProfile.length > 0 && (
        <details className="company-profile">
          <summary>公司画像</summary>
          <div>{insight.companyProfile.map(fact => <p key={fact.label}><strong>{fact.label}：</strong>{fact.value}</p>)}</div>
        </details>
      )}
      <EvidenceStatus insight={insight} />
      {insight.sources.length > 0 && (
        <div className="source-strip">
          <strong>来源</strong>
          {insight.sources.map(url => <a key={url} href={url} target="_blank" rel="noreferrer">{url}</a>)}
        </div>
      )}
      {insight.nextWatchItems.length > 0 && <p><strong>下一步跟踪：</strong>{insight.nextWatchItems.join('、')}</p>}
      {insight.evidenceConflicts.length > 0 && <p className="funding-gap"><strong>证据冲突：</strong>{insight.evidenceConflicts.join('、')}</p>}
      {insight.evidenceGaps.length > 0 && <p className="funding-gap"><strong>证据缺口：</strong>{insight.evidenceGaps.join('、')}</p>}
    </div>
  )
}

function EvidenceStatus({ insight }) {
  const status = insight.evidenceStatus
  return (
    <div className="evidence-status">
      <strong>证据状态</strong>
      <span>来源 {status.sourceCount}</span>
      <span>官方 {status.officialSourceCount}</span>
      <span>独立 {status.independentSourceCount}</span>
      <span>证据 {status.evidenceScore}/100</span>
      <span>完整度 {status.completenessScore}/100</span>
      <span>综合 {insight.scores.overall}/100</span>
    </div>
  )
}

function QuickRead({ item, type }) {
  const read = quickRead(item, type)
  return (
    <div className="quick-read">
      <div className="quick-read-title">↯ 速读摘要</div>
      <p><strong>核心内容：</strong>{read.core}</p>
      {read.facts.length > 0 && (
        <>
          <strong>关键信息：</strong>
          <ul>
            {read.facts.map(value => <li key={value}>{value}</li>)}
          </ul>
        </>
      )}
      <p><strong>值得关注：</strong>{read.watch}</p>
    </div>
  )
}

function Meta({ values }) {
  const clean = values.filter(Boolean)
  if (!clean.length) return null
  return <div className="meta-row">{clean.map(value => <span key={value}>{value}</span>)}</div>
}

function Sources({ report }) {
  const strategy = report.source_strategy || {}
  const errors_by_source = report.errors_by_source || {}
  return (
    <div className="venture-sources">
      <SourceBlock title="Primary Sources" values={strategy.primary_sources || []} />
      <SourceBlock title="Secondary Sources" values={strategy.secondary_sources || []} />
      {strategy.notes && <p className="strategy-note">{strategy.notes}</p>}
      <SourceBlock title="WebSearch Queries" values={strategy.websearch_queries || []} />
      <div className="source-links">
        <h3>来源链接</h3>
        {(report.source_links || []).map((item, index) => (
          <a key={`${item.url}-${index}`} href={item.url} target="_blank" rel="noreferrer">
            <strong>{item.title || item.source_name || item.url}</strong>
            <span>{item.source_name || item.source_type || 'source'} · {item.published_at || ''}</span>
          </a>
        ))}
      </div>
      <div className="source-errors">
        <h3>数据问题</h3>
        {Object.keys(errors_by_source).length === 0 ? <p>无 source errors</p> : Object.entries(errors_by_source).map(([source, values]) => (
          <div key={source}><strong>{source}</strong>: {(Array.isArray(values) ? values : [values]).join('；')}</div>
        ))}
      </div>
      {(report.evidence_conflicts || []).length > 0 && <SourceBlock title="Evidence Conflicts" values={report.evidence_conflicts} />}
    </div>
  )
}

function SourceBlock({ title, values }) {
  if (!values.length) return null
  return (
    <div className="source-block">
      <h3>{title}</h3>
      <div>{values.map(value => <span key={String(value)}>{String(value)}</span>)}</div>
    </div>
  )
}

function WatchItems({ report }) {
  const next_watch_items = report.next_watch_items || []
  const research_plan = report.research_plan || []
  return (
    <div className="watch-grid">
      <WatchList title="Next Watch Items" values={next_watch_items} />
      <WatchList title="Research Plan" values={research_plan} />
    </div>
  )
}

function WatchList({ title, values }) {
  return (
    <section className="watch-list">
      <h3>{title}</h3>
      {values.length === 0 ? <p>暂无条目</p> : <ol>{values.map((value, index) => {
        const text = formatWatchValue(value)
        return <li key={`${index}-${text}`}>{text}</li>
      })}</ol>}
    </section>
  )
}

function formatDate(value) {
  return String(value || '').slice(0, 10) || 'unknown date'
}

function formatPercent(value) {
  const number = Number(value || 0)
  return `${Math.round(number * 100)}%`
}

function formatScore(value) {
  return `${Math.round(Number(value || 0))}`
}

function typeLabel(type) {
  if (type === 'funding') return '融资'
  if (type === 'signal') return '信号'
  return '产品'
}

function stageLabel(stage) {
  if (stage === 'verified') return '已验证'
  if (stage === 'watchlist') return '待验证'
  if (stage === 'candidate') return '候选'
  if (stage === 'rejected') return '已拒绝'
  return ''
}

function statusLabel(status) {
  const labels = {
    rumor: '传闻',
    in_talks: '洽谈中',
    filed: '已提交',
    announced: '已宣布',
    closed: '已完成',
    cancelled: '已取消',
    unclear: '状态不明',
  }
  return labels[status] || status
}

function confidenceLabel(confidence) {
  const labels = { high: '高置信', medium: '中置信', low: '低置信' }
  return labels[String(confidence || '').toLowerCase()] || '置信度未知'
}

const STYLES = `
.venture-page { padding: 22px 26px; color: var(--text-primary); font-size: 13px; }
.venture-header { display: flex; justify-content: space-between; gap: 16px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }
.venture-header h1 { margin: 0 0 8px; font-size: 23px; line-height: 1.25; }
.venture-header p { margin: 0; color: var(--text-muted); font-size: 12px; line-height: 1.55; }
.venture-kicker { color: var(--accent-blue) !important; font-size: 10px !important; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.venture-error { color: #b91c1c; font-size: 12px; margin-bottom: 12px; }
.venture-stats { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 9px; margin-bottom: 14px; }
.venture-stat { border: 1px solid var(--border); border-radius: 8px; padding: 12px 13px; background: var(--bg-secondary); }
.venture-stat strong { display: block; font-size: 15px; line-height: 1.25; }
.venture-stat span { color: var(--text-muted); font-size: 10px; }
.venture-layout { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; }
.venture-report { min-height: 520px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); padding: 16px; }
.week-context { display: flex; flex-wrap: wrap; gap: 8px 10px; align-items: center; margin-bottom: 14px; color: var(--text-muted); font-size: 11px; }
.week-context strong { color: var(--text-primary); font-size: 12px; }
.week-context div { display: flex; flex-wrap: wrap; gap: 6px; }
.week-context span { border: 1px solid var(--border); border-radius: 999px; padding: 3px 8px; background: var(--bg-primary); line-height: 1.35; }
.venture-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 14px; }
.venture-tabs button { display: inline-flex; align-items: center; gap: 7px; border: 1px solid transparent; border-radius: 8px; padding: 9px 12px; background: transparent; color: var(--text-secondary); cursor: pointer; font-size: 13px; line-height: 1.2; }
.venture-tabs button strong { font-size: 13px; }
.venture-tabs button em { font-style: normal; font-size: 13px; opacity: .72; }
.venture-tabs button:hover { background: var(--bg-primary); border-color: var(--border); }
.venture-tabs button.active { background: var(--accent-blue); color: white; border-color: var(--accent-blue); }
.verified-type-tabs { display: inline-flex; flex-wrap: wrap; gap: 4px; margin: -4px 0 14px; padding: 3px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-primary); }
.verified-type-tabs button { display: inline-flex; align-items: center; gap: 6px; min-height: 30px; border: 0; border-radius: 6px; padding: 5px 10px; background: transparent; color: var(--text-secondary); cursor: pointer; font-size: 12px; line-height: 1.2; }
.verified-type-tabs button strong { font-size: 12px; }
.verified-type-tabs button em { font-style: normal; color: var(--text-muted); }
.verified-type-tabs button.active { background: #eff6ff; color: var(--accent-blue); }
.verified-type-tabs button.active em { color: var(--accent-blue); }
.venture-cards { display: grid; gap: 14px; }
.venture-card { display: block; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-primary); color: inherit; text-decoration: none; overflow: hidden; }
.venture-card:hover { border-color: var(--accent-blue); box-shadow: 0 0 0 1px rgba(37, 99, 235, .18); }
.card-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--border); background: var(--bg-secondary); }
    .type, .confidence, .status-pill, .stage-pill, .sector-pill { border-radius: 999px; padding: 3px 8px; font-size: 12px; line-height: 1.35; background: #eef2ff; color: #3730a3; }
    .stage-pill { background: #f3f4f6; color: var(--text-secondary); }
    .stage-pill.watchlist { background: #fff7ed; color: #9a3412; }
    .stage-pill.verified { background: #ecfdf5; color: #166534; }
    .sector-pill { background: #f5f3ff; color: #6d28d9; }
    .status-pill { margin-right: auto; background: #f3f4f6; color: var(--text-secondary); }
    .sector-pill + .confidence, .status-pill + .confidence, .stage-pill + .confidence { margin-left: auto; }
.confidence.low { background: #fef3c7; color: #92400e; }
.confidence.medium { background: #dbeafe; color: #1d4ed8; }
.confidence.high { background: #dcfce7; color: #166534; }
    .venture-card h3 { margin: 18px 20px 10px; font-size: 16px; line-height: 1.45; overflow-wrap: anywhere; }
    .venture-card h3 a { color: inherit; text-decoration: none; }
    .venture-card h3 a:hover { color: var(--accent-blue); }
.venture-card p { margin: 0 20px 14px; color: var(--text-secondary); line-height: 1.65; font-size: 13px; }
.meta-row { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 20px 16px; }
.meta-row span { font-size: 12px; border: 1px solid var(--border); border-radius: 999px; padding: 3px 8px; color: var(--text-muted); line-height: 1.35; }
.quick-read { margin: 0 20px 18px; padding: 14px 16px; border-left: 3px solid #22c55e; border-radius: 8px; background: #f0fdf4; color: #166534; }
.quick-read-title { margin-bottom: 9px; color: #15803d; font-size: 13px; font-weight: 700; }
.quick-read p { margin: 0 0 9px; color: #166534; font-size: 13px; line-height: 1.65; }
.quick-read p:last-child { margin-bottom: 0; }
.quick-read strong { color: #14532d; }
.quick-read ul { margin: 7px 0 10px 18px; padding: 0; }
.quick-read li { margin-bottom: 5px; line-height: 1.55; font-size: 13px; }
    .funding-intel { margin: 0 20px 18px; padding: 14px 16px; border: 1px solid var(--border); border-left: 3px solid var(--accent-blue); border-radius: 8px; background: #fff; color: var(--text-primary); }
.funding-intel p { margin: 12px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.65; }
.funding-intel strong { color: var(--text-primary); }
.quick-read-title.small { margin-top: 12px; margin-bottom: 8px; font-size: 12px; }
.intel-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
.intel-grid div { display: grid; gap: 3px; padding: 9px 10px; border: 1px solid var(--border-light); border-radius: 6px; background: #fafafa; }
.intel-grid span { color: #15803d; font-size: 11px; }
.intel-grid strong { color: var(--text-primary); font-size: 12px; line-height: 1.5; font-weight: 600; }
.funding-facts { display: flex; flex-wrap: wrap; gap: 6px; }
.funding-facts span { border: 1px solid #bfdbfe; border-radius: 999px; padding: 3px 8px; background: #eff6ff; color: #1d4ed8; font-size: 12px; line-height: 1.35; }
.evidence-status, .source-strip { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 12px; }
.evidence-status strong, .source-strip strong { margin-right: 2px; font-size: 12px; color: var(--text-primary); }
.evidence-status span { border: 1px solid var(--border); border-radius: 999px; padding: 3px 8px; background: #fafafa; color: var(--text-secondary); font-size: 12px; line-height: 1.35; }
    .source-strip a { max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; border: 1px solid var(--border); border-radius: 999px; padding: 3px 8px; background: #fafafa; color: var(--accent-blue); font-size: 12px; line-height: 1.35; text-decoration: none; }
    .company-profile { margin-top: 12px; border-top: 1px solid var(--border); padding-top: 10px; }
    .company-profile summary { cursor: pointer; color: var(--text-secondary); font-size: 12px; font-weight: 700; }
    .company-profile div { display: grid; gap: 6px; margin-top: 8px; }
    .company-profile p { margin: 0; }
.funding-gap { color: #92400e !important; }
.funding-gap strong { color: #78350f; }
.gaps { margin: 0 20px 18px; font-size: 13px; color: #92400e; }
.venture-empty { padding: 16px; color: var(--text-muted); }
.venture-empty.large { display: grid; place-items: center; min-height: 360px; text-align: center; }
.source-block, .source-links, .source-errors, .watch-list { border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px; background: var(--bg-primary); }
.source-block h3, .source-links h3, .source-errors h3, .watch-list h3 { margin: 0 0 10px; font-size: 13px; }
.source-block div { display: flex; flex-wrap: wrap; gap: 6px; }
.source-block span { border: 1px solid var(--border); border-radius: 999px; padding: 4px 8px; font-size: 12px; }
.source-links { display: grid; gap: 8px; }
.source-links a { display: grid; gap: 2px; color: var(--accent-blue); text-decoration: none; overflow-wrap: anywhere; }
.source-links a strong { font-size: 13px; line-height: 1.45; }
.source-links a span { color: var(--text-muted); font-size: 12px; }
.strategy-note { color: var(--text-muted); }
.watch-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.watch-list p, .source-errors p, .source-errors div { font-size: 13px; line-height: 1.55; }
.watch-list li { margin-bottom: 8px; line-height: 1.55; font-size: 13px; }
@media (max-width: 980px) {
  .venture-layout { grid-template-columns: 1fr; }
  .venture-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .intel-grid { grid-template-columns: 1fr; }
  .watch-grid { grid-template-columns: 1fr; }
}
`
