import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useShareSelection, ShareSelectionBar } from './useShareSelection'

const TYPE_STYLES = {
  business: { label: '商业机会', color: '#16a34a', bg: '#f0fdf4' },
  '研发提效': { label: '研发提效', color: '#2563eb', bg: '#eff6ff' },
  '业务赋能': { label: '业务赋能', color: '#d97706', bg: '#fffbeb' },
  default: { label: '机会', color: '#6b7280', bg: '#f9fafb' },
}

const SCORE_LABELS = {
  business: [
    ['pain_point', '痛点'],
    ['market_size', '市场'],
    ['tech_timing', '时机'],
    ['buildability', '可做'],
  ],
  rdev: [
    ['efficiency', '效率'],
    ['feasibility', '可行'],
    ['business_impact', '影响'],
    ['overall', '综合'],
  ],
}

function normalizeBusiness(item) {
  return {
    id: `business-${item.item_id || item.opportunity_title}`,
    rawId: item.item_id || item.opportunity_title,
    kind: 'business',
    type: 'business',
    title: item.opportunity_title,
    trigger: item.core_insight,
    scenario: item.product_form,
    solution: item.business_model,
    implementation: '',
    audience: item.target_users ? [item.target_users] : [],
    impact: item.business_model,
    resistance: item.risks,
    features: item.mvp_features || [],
    scores: item.scores || {},
    totalScore: item.total_score || 0,
    scoreMax: 20,
    source: item.source,
    sourceTitle: item.source_title,
    sourceUrl: item.source_url,
  }
}

function normalizeRdev(item) {
  return {
    id: `rdev-${item.item_id || item.title}`,
    kind: 'rdev',
    type: item.type,
    title: item.title,
    trigger: item.trigger,
    scenario: item.scenario,
    solution: item.ai_solution,
    implementation: item.implementation,
    audience: item.audience || [],
    impact: item.impact,
    resistance: item.resistance,
    features: [],
    scores: item.scores || {},
    totalScore: item.total_score || item.scores?.overall || 0,
    scoreMax: 10,
    source: item.source,
    sourceTitle: item.source_title,
    sourceUrl: item.source_url,
  }
}

function OpportunityDashboard() {
  const { date } = useParams()
  const { signalIds, opportunityIds, toggleOpportunity, clearAll, generating, generate } = useShareSelection(date)
  const [business, setBusiness] = useState([])
  const [rdev, setRdev] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeType, setActiveType] = useState('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const [businessRes, rdevRes] = await Promise.all([
          fetch(`/api/briefing/${date}/opportunities`),
          fetch(`/api/briefing/${date}/rdev-opportunities`),
        ])
        const [businessData, rdevData] = await Promise.all([
          businessRes.ok ? businessRes.json() : Promise.resolve({ opportunities: [] }),
          rdevRes.ok ? rdevRes.json() : Promise.resolve({ solutions: [] }),
        ])
        if (!cancelled) {
          setBusiness((businessData.opportunities || []).map(normalizeBusiness))
          setRdev((rdevData.solutions || []).map(normalizeRdev))
        }
      } catch (error) {
        console.error('Failed to fetch opportunities:', error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [date])

  const allItems = useMemo(() => [...business, ...rdev], [business, rdev])
  const types = useMemo(() => Array.from(new Set(allItems.map(item => item.type))), [allItems])
  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase()
    return allItems
      .filter(item => activeType === 'all' || item.type === activeType)
      .filter(item => !q || [item.title, item.trigger, item.scenario, item.solution, item.sourceTitle].some(text => (text || '').toLowerCase().includes(q)))
      .sort((a, b) => (b.totalScore / b.scoreMax) - (a.totalScore / a.scoreMax))
  }, [activeType, allItems, search])

  const avgScore = allItems.length
    ? (allItems.reduce((sum, item) => sum + item.totalScore / item.scoreMax, 0) / allItems.length * 10).toFixed(1)
    : '0.0'

  return (
    <>
      <header className="sticky top-0 z-20 px-6 py-4 border-b"
        style={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-4 mb-4">
          <div className="window-dots">
            <span className="window-dot window-dot-red" />
            <span className="window-dot window-dot-yellow" />
            <span className="window-dot window-dot-green" />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Link to="/" style={{ color: 'var(--text-primary)' }}>TokenBurner</Link>
            <span style={{ color: 'var(--text-muted)' }}>/</span>
            <Link to={`/briefing/${date}`} style={{ color: 'var(--text-primary)' }}>{date}</Link>
            <span style={{ color: 'var(--text-muted)' }}>/</span>
            <span style={{ color: 'var(--accent-blue)' }}>全部机会</span>
          </div>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>商业机会与研发提效机会合并看板</p>
          <ShareSelectionBar
            signalIds={signalIds}
            opportunityIds={opportunityIds}
            generating={generating}
            onClear={clearAll}
            onGenerate={generate}
          />
      </header>

      <main className="opportunity-page">
        <section className="opportunity-hero">
          <div>
            <h1>AI 机会看板</h1>
            <p>基于 {date} 情报分析结果，按评分、类型和关键词快速筛选可落地机会。</p>
          </div>
          <div className="opportunity-stats">
            <Stat label="总机会" value={allItems.length} color="#2563eb" />
            <Stat label="商业机会" value={business.length} color="#16a34a" />
            <Stat label="研发机会" value={rdev.length} color="#d97706" />
            <Stat label="平均评分" value={`${avgScore}分`} color="#7c3aed" />
          </div>
        </section>

        <section className="opportunity-toolbar">
          <div className="opportunity-tabs">
            <button className={activeType === 'all' ? 'active' : ''} onClick={() => setActiveType('all')}>全部</button>
            {types.map(type => (
              <button key={type} className={activeType === type ? 'active' : ''} onClick={() => setActiveType(type)}>
                {(TYPE_STYLES[type] || TYPE_STYLES.default).label}
              </button>
            ))}
          </div>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索标题、场景、方案..." />
        </section>

        {loading ? (
          <div className="opportunity-empty">
            <span className="loading-pulse">▌</span>
            <span>加载机会中...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="opportunity-empty">暂无匹配机会</div>
        ) : (
          <section className="opportunity-grid">
            {filteredItems.map(item => (
              <OpportunityCard
                key={item.id}
                item={item}
                onOpen={() => setSelected(item)}
                selected={item.kind === 'business' && opportunityIds.includes(item.rawId)}
                onToggle={item.kind === 'business'
                  ? (e) => { e.stopPropagation(); toggleOpportunity(item.rawId) }
                  : null}
              />
            ))}
          </section>
        )}
      </main>

      {selected && <OpportunityDetail item={selected} onClose={() => setSelected(null)} />}
    </>
  )
}

function Stat({ label, value, color }) {
  return (
    <div className="opportunity-stat">
      <div style={{ color }}>{value}</div>
      <span>{label}</span>
    </div>
  )
}

function OpportunityCard({ item, onOpen, selected = false, onToggle }) {
  const style = TYPE_STYLES[item.type] || TYPE_STYLES.default
  const labels = SCORE_LABELS[item.kind === 'business' ? 'business' : 'rdev']

  return (
  <article
    className="opportunity-card"
    onClick={onOpen}
    style={selected ? { outline: '1px solid #16a34a', outlineOffset: '-1px' } : {}}
  >
      <div className="opportunity-card-top">
        {onToggle && (
          <button
            onClick={onToggle}
            title={selected ? '取消选择' : '加入分享页'}
            style={{
              width: 16, height: 16, borderRadius: 3, flexShrink: 0,
              border: `1.5px solid ${selected ? '#16a34a' : '#4b5563'}`,
              background: selected ? '#16a34a' : 'transparent',
              color: 'white', fontSize: 9,
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: 0,
            }}
          >
            {selected && '✓'}
          </button>
        )}
        <span className="opportunity-type" style={{ color: style.color, backgroundColor: style.bg }}>{style.label}</span>
        <span className="opportunity-score">{item.totalScore}/{item.scoreMax}</span>
      </div>
      <h2>{item.title}</h2>
      {item.trigger && <p className="opportunity-insight">{item.trigger}</p>}
      {item.scenario && (
        <div className="opportunity-section">
          <span>场景</span>
          <p>{item.scenario}</p>
        </div>
      )}
      {item.solution && (
        <div className="opportunity-section">
          <span>{item.kind === 'business' ? '模式' : '方案'}</span>
          <p>{item.solution}</p>
        </div>
      )}
      <div className="opportunity-score-list">
        {labels.map(([key, label]) => (
          <ScoreBar key={key} label={label} value={item.scores?.[key] || 0} max={item.kind === 'business' ? 5 : 10} />
        ))}
      </div>
      <div className="opportunity-card-footer">
        <span>{item.source}</span>
        <span>{item.audience.slice(0, 2).join(' / ')}</span>
      </div>
    </article>
  )
}

function ScoreBar({ label, value, max }) {
  return (
    <div className="opportunity-score-row">
      <span>{label}</span>
      <div><i style={{ width: `${Math.min(100, (value / max) * 100)}%` }} /></div>
      <b>{value}</b>
    </div>
  )
}

function OpportunityDetail({ item, onClose }) {
  const style = TYPE_STYLES[item.type] || TYPE_STYLES.default
  return (
    <div className="opportunity-detail-backdrop" onClick={onClose}>
      <aside className="opportunity-detail" onClick={e => e.stopPropagation()}>
        <button className="opportunity-detail-close" onClick={onClose}>×</button>
        <span className="opportunity-type" style={{ color: style.color, backgroundColor: style.bg }}>{style.label}</span>
        <h2>{item.title}</h2>
        <DetailBlock title="触发洞察" text={item.trigger} />
        <DetailBlock title="应用场景" text={item.scenario} />
        <DetailBlock title={item.kind === 'business' ? '商业模式' : 'AI 解决方案'} text={item.solution} />
        <DetailBlock title="实施方案" text={item.implementation} />
        <DetailBlock title="预期影响" text={item.impact} />
        <DetailBlock title="潜在阻力/风险" text={item.resistance} />
        {item.features.length > 0 && (
          <div className="opportunity-detail-block">
            <h3>MVP 功能</h3>
            <ul>
              {item.features.map((feature, index) => <li key={index}>{feature}</li>)}
            </ul>
          </div>
        )}
        {item.audience.length > 0 && (
          <div className="opportunity-tags">
            {item.audience.map(audience => <span key={audience}>{audience}</span>)}
          </div>
        )}
        {item.sourceUrl && (
          <a className="opportunity-source-link" href={item.sourceUrl} target="_blank" rel="noopener noreferrer">
            查看来源：{item.sourceTitle || item.source}
          </a>
        )}
      </aside>
    </div>
  )
}

function DetailBlock({ title, text }) {
  if (!text) return null
  return (
    <div className="opportunity-detail-block">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  )
}

export default OpportunityDashboard
