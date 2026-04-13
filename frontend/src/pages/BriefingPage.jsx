import { useEffect, useState, useMemo, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

const CATEGORY_TABS = [
  { key: 'all', label: '全部', icon: '∗' },
  { key: 'paper', label: '论文', icon: '📄' },
  { key: 'repo', label: '仓库', icon: '🛠️' },
  { key: 'model', label: '模型', icon: '🤖' },
  { key: 'news', label: '资讯', icon: '📰' },
  { key: 'blog', label: 'AI公司博客', icon: '🏢' },
  { key: 'wechat', label: '微信公众号', icon: '💬' },
  { key: 'smolai', label: 'Smol资讯', icon: '⚡' }
]

const SOURCE_TYPE_MAP = {
  arxiv: { label: '论文', badge: 'badge-paper' },
  paper: { label: '论文', badge: 'badge-paper' },
  repo: { label: '仓库', badge: 'badge-repo' },
  github: { label: '仓库', badge: 'badge-repo' },
  model: { label: '模型', badge: 'badge-model' },
  rss: { label: '资讯', badge: 'badge-news' },
  smolai: { label: 'Smol资讯', badge: 'badge-smolai' },
  newsletter: { label: '资讯', badge: 'badge-news' },
  tweet: { label: '动态', badge: 'badge-news' },
  podcast: { label: '播客', badge: 'badge-news' },
  news: { label: '资讯', badge: 'badge-news' },
  blog: { label: '官方博客', badge: 'badge-model' },
  wechat: { label: '公众号', badge: 'badge-news' }
}


function BriefingPage() {
  const { date } = useParams()
  const [briefing, setBriefing] = useState(null)
  const [activeCategory, setActiveCategory] = useState('all')
  const [loading, setLoading] = useState(true)
  const [digest, setDigest] = useState(null)
  const [digestLoading, setDigestLoading] = useState(false)
  const [opportunities, setOpportunities] = useState([])
  const [oppsLoading, setOppsLoading] = useState(false)
  const [oppsRemaining, setOppsRemaining] = useState(null) // 剩余未分析条目数
  const [searchingOpps, setSearchingOpps] = useState(false)
  const [quickReads, setQuickReads] = useState({}) // { item_id: summary }
  const [batchGenerating, setBatchGenerating] = useState(false)
  const [rdev, setRdev] = useState(null)
  const [rdevLoading, setRdevLoading] = useState(false)
  const [rdevRemaining, setRdevRemaining] = useState(null)
  const [searchingRdev, setSearchingRdev] = useState(false)

  useEffect(() => {
    fetchData()
  }, [date])

  async function fetchData() {
    setLoading(true)
    try {
      const res = await fetch(`/api/briefing/${date}`)
      const briefingData = await res.json()
      setBriefing(briefingData)
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
    fetchDigest()
    fetchOpportunities()
    fetchRdev()
    // 加载已缓存的速读，然后触发后台批量生成
    fetch(`/api/content/quick-reads/${date}`)
      .then(r => r.ok ? r.json() : {})
      .then(data => {
        setQuickReads(data)
        triggerBatchAndPoll()
      })
      .catch(() => triggerBatchAndPoll())
  }

  async function triggerBatchAndPoll() {
    setBatchGenerating(true)
    try {
      const res = await fetch(`/api/briefing/${date}/batch-quick-reads`, { method: 'POST' })
      if (!res.ok) return
      const result = await res.json()
      if (result.generated > 0) {
        // 有新生成的，刷新缓存
        const qr = await fetch(`/api/content/quick-reads/${date}`)
        if (qr.ok) setQuickReads(await qr.json())
      }
    } catch (e) {
      console.error('[batch-quick-reads]', e)
    } finally {
      setBatchGenerating(false)
    }
  }

  async function fetchRdev(refresh = false) {
    setRdevLoading(true)
    try {
      const res = await fetch(`/api/briefing/${date}/rdev-opportunities${refresh ? '?refresh=true' : ''}`)
      if (res.ok) {
        const data = await res.json()
        setRdev(data)
        setRdevRemaining(data.remaining ?? null)
      }
    } catch (e) {
      console.error('Failed to fetch rdev opportunities:', e)
    } finally {
      setRdevLoading(false)
    }
  }

  async function searchMoreRdev() {
    setSearchingRdev(true)
    try {
      const res = await fetch(`/api/briefing/${date}/rdev-opportunities/search`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setRdev(data)
        setRdevRemaining(data.remaining ?? null)
      }
    } catch (e) {
      console.error('Failed to search rdev opportunities:', e)
    } finally {
      setSearchingRdev(false)
    }
  }

  async function fetchDigest(refresh = false) {
    setDigestLoading(true)
    try {
      const res = await fetch(`/api/briefing/${date}/category-digest${refresh ? '?refresh=true' : ''}`)
      if (res.ok) setDigest(await res.json())
    } catch (e) {
      console.error('Failed to fetch digest:', e)
    } finally {
      setDigestLoading(false)
    }
  }

  async function fetchOpportunities(refresh = false) {
    setOppsLoading(true)
    try {
      const res = await fetch(`/api/briefing/${date}/opportunities${refresh ? '?refresh=true' : ''}`)
      if (res.ok) {
        const data = await res.json()
        setOpportunities(data.opportunities || [])
        setOppsRemaining(data.remaining ?? null)
      }
    } catch (e) {
      console.error('Failed to fetch opportunities:', e)
    } finally {
      setOppsLoading(false)
    }
  }

  async function searchMoreOpportunities() {
    setSearchingOpps(true)
    try {
      const res = await fetch(`/api/briefing/${date}/opportunities/search`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setOpportunities(data.opportunities || [])
        setOppsRemaining(data.remaining ?? null)
      }
    } catch (e) {
      console.error('Failed to search opportunities:', e)
    } finally {
      setSearchingOpps(false)
    }
  }

  const filteredItems = useMemo(() => {
    if (!briefing) return []
    const items = briefing.items || []
    if (activeCategory === 'all') return items
    return items.filter(item => {
      const type = item.source_type
      if (activeCategory === 'paper') return type === 'arxiv' || type === 'paper'
      if (activeCategory === 'repo') return type === 'repo' || type === 'github'
      if (activeCategory === 'model') return type === 'model'
      if (activeCategory === 'blog') return type === 'blog'
      if (activeCategory === 'wechat') return type === 'wechat'
      if (activeCategory === 'smolai') return type === 'smolai'
      if (activeCategory === 'news') return ['rss', 'newsletter', 'tweet', 'podcast', 'news'].includes(type)
      return true
    })
  }, [briefing, activeCategory])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
          <span className="loading-pulse">▌</span>
          <span className="text-sm">加载中...</span>
        </div>
      </div>
    )
  }

  if (!briefing) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <div className="window-dots justify-center mb-4">
            <span className="window-dot window-dot-red" />
            <span className="window-dot window-dot-yellow" />
            <span className="window-dot window-dot-green" />
          </div>
          <h2 className="text-lg font-semibold mb-2">简报未找到</h2>
          <Link to="/" style={{ color: 'var(--accent-blue)' }} className="text-sm">
            返回首页
          </Link>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Header */}
      <header
        className="sticky top-0 z-20 px-6 py-4 border-b"
        style={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-4 mb-4">
          <div className="window-dots">
            <span className="window-dot window-dot-red" />
            <span className="window-dot window-dot-yellow" />
            <span className="window-dot window-dot-green" />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span style={{ color: 'var(--text-primary)' }}>TokenBurner</span>
            <span style={{ color: 'var(--text-muted)' }}>/</span>
            <span style={{ color: 'var(--accent-blue)' }}>{date}</span>
            <span style={{ color: 'var(--text-muted)' }}>/</span>
            <span style={{ color: 'var(--text-primary)' }}>AI技术日报</span>
          </div>
          {batchGenerating && (
            <span className="ml-auto text-xs flex items-center gap-1" style={{ color: '#16a34a' }}>
              <span className="loading-pulse">▌</span>
              <span>速读生成中...</span>
            </span>
          )}
        </div>
      </header>

      {/* Category Tabs */}
      <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex gap-2">
          {CATEGORY_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveCategory(tab.key)}
              className={`tab-btn ${activeCategory === tab.key ? 'active' : ''}`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Category Digest */}
      <CategoryDigest digest={digest} loading={digestLoading} onRefresh={() => fetchDigest(true)} />

      {/* Opportunity Radar */}
      <OpportunityRadar
        opportunities={opportunities}
        loading={oppsLoading}
        onRefresh={() => fetchOpportunities(true)}
        onSearch={searchMoreOpportunities}
        searching={searchingOpps}
        remaining={oppsRemaining}
        date={date}
      />

      {/* R&D Efficiency Insights */}
      <RdevPanel
        data={rdev}
        loading={rdevLoading}
        onRefresh={() => fetchRdev(true)}
        onSearch={searchMoreRdev}
        searching={searchingRdev}
        remaining={rdevRemaining}
      />

      {/* Content */}
      <div className="p-6" style={{ maxWidth: '900px' }}>
        {briefing.summary && (
          <div className="mb-6">
            <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
              AI 技术日报总览
            </h2>
            <div className="markdown-content text-sm" style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              <ReactMarkdown>{briefing.summary}</ReactMarkdown>
            </div>
          </div>
        )}
        <section className="space-y-4">
          {filteredItems.map((item, index) => (
            <ContentCard key={item.id} item={item} index={index + 1}
              cachedSummary={quickReads[item.id]}
              date={date}
              onQuickRead={(id, summary) => setQuickReads(prev => ({ ...prev, [id]: summary }))}
            />
          ))}
        </section>
      </div>
    </>
  )
}

const SOURCE_TYPE_BADGE = {
  arxiv: { label: '论文', color: '#6366f1' },
  paper: { label: '论文', color: '#6366f1' },
  repo:  { label: '仓库', color: '#0ea5e9' },
  github:{ label: '仓库', color: '#0ea5e9' },
  model: { label: '模型', color: '#10b981' },
  rss:   { label: '资讯', color: '#f59e0b' },
  news:  { label: '资讯', color: '#f59e0b' },
}

function ScoreDot({ value }) {
  return (
    <div className="flex gap-0.5">
      {[1,2,3,4,5].map(i => (
        <span key={i} className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: i <= value ? '#3b82f6' : '#e5e7eb' }} />
      ))}
    </div>
  )
}

function OpportunityRadar({ opportunities, loading, onRefresh, onSearch, searching, remaining, date }) {
  const [current, setCurrent] = useState(0)
  const [saved, setSaved] = useState(new Set())
  const [skipped, setSkipped] = useState(new Set())

  // reset when date changes
  useEffect(() => { setCurrent(0); setSaved(new Set()); setSkipped(new Set()) }, [date])

  if (!loading && opportunities.length === 0) return null

  const opp = opportunities[current]
  const total = opportunities.length
  const typeBadge = opp ? (SOURCE_TYPE_BADGE[opp.source_type] || { label: '资讯', color: '#f59e0b' }) : null

  async function handleSave() {
    if (!opp) return
    setSaved(prev => new Set([...prev, current]))
    try {
      const mvpList = (opp.mvp_features || []).map(f => `- ${f}`).join('\n')
      const description = [
        opp.core_insight && `**核心洞察**\n${opp.core_insight}`,
        opp.product_form && `**产品形态**\n${opp.product_form}`,
        opp.target_users && `**目标用户**\n${opp.target_users}`,
        mvpList && `**核心功能（MVP）**\n${mvpList}`,
        opp.business_model && `**商业模式**\n${opp.business_model}`,
        opp.competitive_barrier && `**竞争壁垒**\n${opp.competitive_barrier}`,
        opp.risks && `**潜在风险**\n${opp.risks}`,
      ].filter(Boolean).join('\n\n')
      await fetch('/api/experiments/ideas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: opp.opportunity_title,
          description,
          difficulty: 'medium',
          estimated_days: 7,
          tags: [],
          status: 'pending',
          priority: opp.total_score,
          source_title: opp.source_title,
          source_url: opp.source_url,
          source_type: opp.source_type,
        })
      })
    } catch (e) {
      console.error('save opportunity failed:', e)
    }
    if (current < total - 1) setCurrent(c => c + 1)
  }

  function handleSkip() {
    setSkipped(prev => new Set([...prev, current]))
    if (current < total - 1) setCurrent(c => c + 1)
  }

  return (
    <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            机会雷达
          </span>
          {!loading && total > 0 && (
            <span className="text-xs font-mono px-1.5 py-0.5 rounded"
              style={{ backgroundColor: '#eff6ff', color: '#3b82f6' }}>
              {total} 个机会
            </span>
          )}
          {remaining !== null && remaining > 0 && !searching && (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              还有 {remaining} 条未分析
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {remaining !== 0 && (
            <button onClick={onSearch} disabled={searching || loading}
              className="text-xs px-3 py-1.5 rounded border font-medium transition-all"
              style={{
                color: '#16a34a',
                borderColor: '#22c55e',
                backgroundColor: searching ? '#dcfce7' : '#f0fdf4',
                opacity: searching ? 1 : 1,
                boxShadow: searching ? '0 0 0 2px #bbf7d0' : 'none',
              }}>
              {searching
                ? <span className="flex items-center gap-1.5">
                    <span style={{ animation: 'pulse 1s ease-in-out infinite' }}>●</span>
                    搜索中...
                  </span>
                : '⊕ 搜索机会'}
            </button>
          )}
          <button onClick={onRefresh} disabled={loading || searching}
            className="text-xs disabled:opacity-40" style={{ color: 'var(--text-muted)' }}>
            {loading ? '分析中...' : '↺ 重新分析'}
          </button>
        </div>
      </div>

      {/* 搜索新机会时的 overlay */}
      {searching && (
        <div className="rounded-xl border mb-3 overflow-hidden"
          style={{ borderColor: '#86efac', backgroundColor: '#f0fdf4' }}>
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <div className="flex items-center gap-2">
              {[0, 1, 2, 3, 4].map(i => (
                <span key={i} className="w-2 h-2 rounded-full"
                  style={{
                    backgroundColor: '#16a34a',
                    animation: `pulse 1.2s ease-in-out ${i * 0.15}s infinite`,
                    opacity: 0.7,
                  }} />
              ))}
            </div>
            <p className="text-sm font-medium" style={{ color: '#16a34a' }}>
              AI 正在从新情报中搜索商业机会...
            </p>
            <p className="text-xs" style={{ color: '#86efac' }}>
              约需 20-40 秒，搜索完成后自动更新
            </p>
          </div>
        </div>
      )}

      {loading && opportunities.length === 0 ? (
        <div className="flex items-center gap-2 py-6 justify-center text-sm" style={{ color: 'var(--text-muted)' }}>
          <span className="loading-pulse">▌</span>
          <span>AI 正在分析商业机会，约需 20-30 秒...</span>
        </div>
      ) : opp ? (
        <div className="flex items-start gap-4" style={{ opacity: searching ? 0.4 : 1, pointerEvents: searching ? 'none' : 'auto', transition: 'opacity 0.3s' }}>
          {/* Card */}
          <div className="flex-1 rounded-xl border overflow-hidden"
            style={{ backgroundColor: 'white', borderColor: 'var(--border)' }}>
            {/* Card header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b"
              style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{ backgroundColor: typeBadge.color + '18', color: typeBadge.color }}>
                  {typeBadge.label}
                </span>
                <a href={opp.source_url} target="_blank" rel="noopener noreferrer"
                  className="text-xs truncate max-w-xs" style={{ color: 'var(--text-muted)' }}>
                  {opp.source_title}
                </a>
              </div>
              <div className="flex items-center gap-1.5">
                {saved.has(current) && (
                  <span className="text-xs px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: '#dcfce7', color: '#16a34a' }}>✓ 已保存</span>
                )}
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                  {current + 1} / {total}
                </span>
              </div>
            </div>

            {/* Card body */}
            <div className="p-4 space-y-3 text-sm">
              <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                {opp.opportunity_title}
              </h3>

              {opp.core_insight && (
                <div className="p-3 rounded-lg" style={{ backgroundColor: '#eff6ff', borderLeft: '3px solid #3b82f6' }}>
                  <span className="text-xs font-semibold" style={{ color: '#3b82f6' }}>💡 核心洞察</span>
                  <p className="mt-1 leading-relaxed text-xs" style={{ color: '#1e40af' }}>{opp.core_insight}</p>
                </div>
              )}

              {opp.product_form && (
                <div>
                  <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>产品形态</span>
                  <p className="mt-0.5 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{opp.product_form}</p>
                </div>
              )}

              {opp.target_users && (
                <div>
                  <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>目标用户</span>
                  <p className="mt-0.5 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{opp.target_users}</p>
                </div>
              )}

              {opp.mvp_features?.length > 0 && (
                <div>
                  <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>核心功能 MVP</span>
                  <ul className="mt-1 space-y-0.5">
                    {opp.mvp_features.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5 text-xs" style={{ color: 'var(--text-secondary)' }}>
                        <span style={{ color: '#3b82f6', flexShrink: 0 }}>▸</span>{f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                {opp.business_model && (
                  <div className="p-2 rounded" style={{ backgroundColor: '#f0fdf4' }}>
                    <span className="text-xs font-semibold" style={{ color: '#16a34a' }}>💰 商业模式</span>
                    <p className="mt-0.5 text-xs" style={{ color: '#15803d' }}>{opp.business_model}</p>
                  </div>
                )}
                {opp.competitive_barrier && (
                  <div className="p-2 rounded" style={{ backgroundColor: '#faf5ff' }}>
                    <span className="text-xs font-semibold" style={{ color: '#7c3aed' }}>🛡️ 竞争壁垒</span>
                    <p className="mt-0.5 text-xs" style={{ color: '#6d28d9' }}>{opp.competitive_barrier}</p>
                  </div>
                )}
              </div>

              {opp.risks && (
                <div className="p-2 rounded" style={{ backgroundColor: '#fff7ed' }}>
                  <span className="text-xs font-semibold" style={{ color: '#ea580c' }}>⚠️ 潜在风险</span>
                  <p className="mt-0.5 text-xs" style={{ color: '#c2410c' }}>{opp.risks}</p>
                </div>
              )}

              {/* Scores */}
              <div className="pt-2 border-t grid grid-cols-4 gap-2" style={{ borderColor: 'var(--border-light)' }}>
                {[
                  { key: 'pain_point', label: '痛点' },
                  { key: 'market_size', label: '市场' },
                  { key: 'tech_timing', label: '时机' },
                  { key: 'buildability', label: '可做' },
                ].map(({ key, label }) => (
                  <div key={key} className="flex flex-col gap-1 items-center">
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
                    <ScoreDot value={opp.scores?.[key] || 0} />
                  </div>
                ))}
              </div>
            </div>

            {/* Card footer */}
            <div className="flex border-t" style={{ borderColor: 'var(--border)' }}>
              <button onClick={handleSkip}
                className="flex-1 py-2.5 text-sm font-medium transition-colors hover:bg-red-50"
                style={{ color: '#dc2626', borderRight: '1px solid var(--border)' }}>
                ✕ 跳过
              </button>
              <button onClick={handleSave} disabled={saved.has(current)}
                className="flex-1 py-2.5 text-sm font-medium transition-colors hover:bg-green-50 disabled:opacity-50"
                style={{ color: '#16a34a' }}>
                ♥ 加入想法池
              </button>
            </div>
          </div>

          {/* Side navigation */}
          <div className="flex flex-col gap-2 justify-center pt-16">
            <button onClick={() => setCurrent(c => Math.max(0, c - 1))}
              disabled={current === 0}
              className="w-8 h-8 rounded-full border flex items-center justify-center text-sm disabled:opacity-30 hover:bg-gray-50"
              style={{ borderColor: 'var(--border)' }}>‹</button>
            <button onClick={() => setCurrent(c => Math.min(total - 1, c + 1))}
              disabled={current === total - 1}
              className="w-8 h-8 rounded-full border flex items-center justify-center text-sm disabled:opacity-30 hover:bg-gray-50"
              style={{ borderColor: 'var(--border)' }}>›</button>
          </div>
        </div>
      ) : null}

      {/* Progress dots */}
      {total > 0 && (
        <div className="flex gap-1 mt-3 justify-center flex-wrap">
          {opportunities.map((_, i) => (
            <button key={i} onClick={() => setCurrent(i)}
              className="w-2 h-2 rounded-full transition-all"
              style={{
                backgroundColor: i === current ? '#3b82f6'
                  : saved.has(i) ? '#16a34a'
                  : skipped.has(i) ? '#d1d5db'
                  : '#cbd5e1'
              }} />
          ))}
        </div>
      )}
    </div>
  )
}

const DIGEST_CATEGORIES = [
  { key: 'paper', icon: '📄', label: '论文', accent: '#6366f1', bg: '#eef2ff' },
  { key: 'repo',  icon: '🛠️', label: '仓库', accent: '#0ea5e9', bg: '#e0f2fe' },
  { key: 'model', icon: '🤖', label: '模型', accent: '#10b981', bg: '#d1fae5' },
  { key: 'news',  icon: '📰', label: '资讯', accent: '#f59e0b', bg: '#fef3c7' },
]

function CategoryDigest({ digest, loading, onRefresh }) {
  // 有缓存或正在加载才展示区块
  if (!loading && !digest) return null

  return (
    <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
          今日速览
        </span>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="text-xs disabled:opacity-40"
          style={{ color: 'var(--text-muted)' }}
        >
          {loading ? '生成中...' : '↺ 重新生成'}
        </button>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {DIGEST_CATEGORIES.map(({ key, icon, label, accent, bg }) => {
          const data = digest?.categories?.[key]
          return (
            <div
              key={key}
              className="rounded-xl p-3 border"
              style={{ backgroundColor: bg, borderColor: accent + '40' }}
            >
              <div className="flex items-center gap-1.5 mb-2">
                <span style={{ fontSize: '14px' }}>{icon}</span>
                <span className="text-xs font-semibold" style={{ color: accent }}>{label}</span>
                {data?.count != null && (
                  <span className="text-xs ml-auto font-mono" style={{ color: accent + 'bb' }}>
                    {data.count} 条
                  </span>
                )}
              </div>
              {loading && !data ? (
                <div className="text-xs" style={{ color: accent + '99' }}>生成中...</div>
              ) : data?.summary ? (
                <p className="text-xs leading-relaxed" style={{ color: '#374151' }}>
                  {data.summary}
                </p>
              ) : (
                <p className="text-xs" style={{ color: accent + '88' }}>今日暂无内容</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function GuidedIdeaPopover({ onGenerate, onClose }) {
  const [hint, setHint] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    function handleKey(e) { if (e.key === 'Escape') onClose() }
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('keydown', handleKey)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])

  return (
    <div ref={ref} style={{
      position: 'absolute', bottom: '36px', right: '0',
      width: '240px', zIndex: 50,
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '12px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.3)'
    }}>
      <div className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
        ✏️ 输入你的想法方向（可选）
      </div>
      <textarea
        autoFocus
        value={hint}
        onChange={e => setHint(e.target.value)}
        placeholder="例如：想探索 agent 工具调用的边界…"
        rows={2}
        className="w-full text-xs rounded px-2 py-1.5 resize-none"
        style={{
          border: '1px solid var(--border)',
          background: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          outline: 'none'
        }}
      />
      <div className="flex gap-2 mt-2">
        <button
          onClick={() => onGenerate(hint)}
          className="flex-1 text-xs py-1.5 rounded border transition-colors"
          style={{ color: 'var(--accent-purple, #a78bfa)', borderColor: 'var(--accent-purple, #a78bfa)', background: 'transparent' }}
        >
          引导生成
        </button>
        <button
          onClick={() => onGenerate('')}
          className="flex-1 text-xs py-1.5 rounded border transition-colors"
          style={{ color: 'var(--text-muted)', borderColor: 'var(--border)', background: 'transparent' }}
        >
          直接生成
        </button>
      </div>
    </div>
  )
}

function ContentCard({ item, index, cachedSummary, date, onQuickRead }) {
  const typeInfo = SOURCE_TYPE_MAP[item.source_type] || { label: '资讯', badge: 'badge-news' }
  const [genState, setGenState] = useState('idle') // idle | loading | done | error
  const [genError, setGenError] = useState('')
  const [savedCount, setSavedCount] = useState(0)
  const [generatedIdeas, setGeneratedIdeas] = useState(null) // null | idea[]
  const [quickSummary, setQuickSummary] = useState(cachedSummary || null)
  const [quickState, setQuickState] = useState(cachedSummary ? 'done' : 'idle') // idle | loading | done | error
  const [collapsed, setCollapsed] = useState(false) // 用户手动折叠
  const [popoverOpen, setPopoverOpen] = useState(false)
  const closePopover = useCallback(() => setPopoverOpen(false), [])

  // 当父组件批量生成完成后，更新摘要并展开
  useEffect(() => {
    if (cachedSummary && !quickSummary) {
      setQuickSummary(cachedSummary)
      setQuickState('done')
      setCollapsed(false)
    }
  }, [cachedSummary])

  async function handleQuickRead() {
    if (quickState === 'done') {
      // 已有摘要，切换折叠状态
      setCollapsed(c => !c)
      return
    }
    setQuickState('loading')
    try {
      const res = await fetch('/api/content/quick-read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_id: item.id,
          url: item.url,
          title: item.title,
          date: date,
          existing_summary: item.summary || '',
        })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setQuickSummary(data.summary)
      setQuickState('done')
      onQuickRead?.(item.id, data.summary)
    } catch (e) {
      console.error('[速读] 失败:', e.message)
      setQuickState('error')
      setTimeout(() => setQuickState('idle'), 3000)
    }
  }

  async function generateIdeas(hint = '') {
    setPopoverOpen(false)
    setGenState('loading')
    setGenError('')
    try {
      const body = { item }
      if (hint) body.user_hint = hint
      const res = await fetch('/api/experiments/generate-ideas/item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setGeneratedIdeas(data.ideas || [])
      setGenState('selecting')
    } catch (e) {
      console.error('[生成实验想法] 失败:', e.message)
      setGenError(e.message)
      setGenState('error')
    }
  }

  async function saveSelectedIdeas(selectedIdeas) {
    await Promise.all(selectedIdeas.map(idea =>
      fetch('/api/experiments/ideas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content_id: item.id || '',
          title: idea.title,
          description: `**为什么产生这个想法**\n${idea.why}\n\n**价值**\n${idea.value}\n\n**具体帮助**\n${idea.help}`,
          difficulty: idea.difficulty || 'medium',
          estimated_days: idea.estimated_days || 7,
          tags: idea.tags || [],
          status: 'pending',
          priority: item.relevance_score || 0,
          source_type: item.source_type || '',
          source_title: item.title || '',
          source_url: item.url || ''
        })
      })
    ))
    setSavedCount(selectedIdeas.length)
    setGeneratedIdeas(null)
    setGenState('done')
  }

  return (
    <article className="content-card">
      <div className="card-header">
        <span className="text-sm" style={{ color: 'var(--text-muted)' }}>#{index}</span>
        <span className={`badge ${typeInfo.badge}`}>{typeInfo.label}</span>
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          来源: {item.source}
        </span>
        {item.created_at && (
          <>
            <span style={{ color: 'var(--border)', fontSize: '12px' }}>|</span>
            <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              {new Date(item.created_at).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })}
              {' '}
              {new Date(item.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })}
            </span>
          </>
        )}
        <span className="text-sm ml-auto" style={{ color: 'var(--text-muted)' }}>
          相关度: {item.relevance_score}/10
        </span>
      </div>

      <div className="p-5">
        {/* Title */}
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
          {item.title}
        </h3>

        {/* Summary */}
        {item.summary && (
          <div className="markdown-content text-sm mb-4">
            <ReactMarkdown>{item.summary}</ReactMarkdown>
          </div>
        )}

        {/* Quick Read Summary */}
        {quickState === 'done' && quickSummary && !collapsed && (
          <div className="mb-4 p-3 rounded-lg border-l-2 text-sm"
            style={{ backgroundColor: '#f0fdf4', borderLeftColor: '#22c55e' }}>
            <div className="flex items-center gap-1.5 mb-2">
              <span style={{ fontSize: '12px' }}>⚡</span>
              <span className="text-xs font-semibold" style={{ color: '#16a34a' }}>速读摘要</span>
            </div>
            <div className="markdown-content quick-read-markdown text-sm" style={{ lineHeight: 1.7 }}>
              <ReactMarkdown>{quickSummary}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: 'var(--border-light)' }}>
          <div className="flex flex-wrap gap-2">
            {(item.category || []).slice(0, 4).map((cat) => (
              <span key={cat} className="tag">{cat}</span>
            ))}
          </div>
          <div className="flex items-center gap-2">
            {/* 速读按钮 */}
            <button
              onClick={handleQuickRead}
              disabled={quickState === 'loading'}
              className="text-sm px-2 py-1 rounded border transition-colors disabled:opacity-50"
              style={{
                color: quickState === 'done' ? '#16a34a' : quickState === 'error' ? '#dc2626' : 'var(--text-muted)',
                borderColor: quickState === 'done' ? '#86efac' : quickState === 'error' ? '#fecaca' : 'var(--border)',
                backgroundColor: quickState === 'done' ? '#f0fdf4' : 'transparent'
              }}
            >
              {quickState === 'loading' ? '速读中...'
                : quickState === 'done' ? (collapsed ? '⚡ 展开速读' : '⚡ 收起速读')
                : quickState === 'error' ? '速读失败（重试）'
                : '⚡ 速读'}
            </button>

            {/* 生成实验想法 */}
            {genState === 'done' ? (
              <Link to="/experiments/ideas"
                className="text-sm px-2 py-1 rounded border"
                style={{ color: 'var(--accent-green)', borderColor: 'var(--accent-green)' }}>
                查看想法 ({savedCount})
              </Link>
            ) : (
              <div style={{ position: 'relative' }}>
                {/* 分割按钮 */}
                <div className="flex" style={{ border: '1px solid var(--border)', borderRadius: '5px' }}>
                  {/* 左侧：直接生成 */}
                  <button
                    onClick={genState === 'error' ? () => setGenState('idle') : () => generateIdeas('')}
                    disabled={genState === 'loading' || genState === 'selecting'}
                    className="text-sm px-2 py-1 transition-colors disabled:opacity-50"
                    title={genState === 'error' ? genError : ''}
                    style={{
                      color: genState === 'error' ? '#dc2626' : 'var(--text-muted)',
                      borderRight: '1px solid var(--border)',
                      background: 'transparent',
                      borderTop: 'none', borderBottom: 'none', borderLeft: 'none'
                    }}
                  >
                    {genState === 'loading' ? '⏳ 生成中...'
                      : genState === 'error' ? '生成失败（重试）'
                      : '生成实验想法'}
                  </button>
                  {/* 右侧：弹出引导面板 */}
                  <button
                    onClick={() => setPopoverOpen(o => !o)}
                    disabled={genState === 'loading' || genState === 'selecting' || genState === 'error'}
                    className="text-xs px-1.5 py-1 transition-colors disabled:opacity-30"
                    style={{
                      color: popoverOpen ? 'var(--accent-purple, #a78bfa)' : 'var(--text-muted)',
                      background: popoverOpen ? 'rgba(167,139,250,0.08)' : 'transparent',
                      border: 'none'
                    }}
                  >
                    ▲
                  </button>
                </div>
                {/* 引导面板 */}
                {popoverOpen && (
                  <GuidedIdeaPopover
                    onGenerate={generateIdeas}
                    onClose={closePopover}
                  />
                )}
              </div>
            )}

            {/* 想法选择弹窗 */}
            {genState === 'selecting' && generatedIdeas && (
              <IdeasSelectModal
                ideas={generatedIdeas}
                sourceTitle={item.title}
                onConfirm={saveSelectedIdeas}
                onCancel={() => { setGeneratedIdeas(null); setGenState('idle') }}
              />
            )}

            <a href={item.url} target="_blank" rel="noopener noreferrer"
              className="text-sm" style={{ color: 'var(--accent-blue)' }}>
              阅读原文 →
            </a>
          </div>
        </div>
      </div>
    </article>
  )
}

const DIFFICULTY_LABEL = { easy: '简单', medium: '中等', hard: '困难' }
const DIFFICULTY_COLOR = { easy: '#16a34a', medium: '#d97706', hard: '#dc2626' }

function IdeasSelectModal({ ideas, sourceTitle, onConfirm, onCancel }) {
  const [selected, setSelected] = useState(new Set(ideas.map((_, i) => i)))
  const [saving, setSaving] = useState(false)

  function toggleAll() {
    setSelected(prev => prev.size === ideas.length ? new Set() : new Set(ideas.map((_, i) => i)))
  }

  function toggle(i) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })
  }

  async function handleConfirm() {
    if (selected.size === 0) return
    setSaving(true)
    await onConfirm(ideas.filter((_, i) => selected.has(i)))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      onClick={e => e.target === e.currentTarget && onCancel()}>
      <div className="w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden"
        style={{ backgroundColor: 'var(--bg-primary)', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>

        {/* Header */}
        <div className="px-6 py-4 border-b flex items-start justify-between gap-4"
          style={{ borderColor: 'var(--border)' }}>
          <div>
            <h2 className="text-base font-semibold mb-0.5" style={{ color: 'var(--text-primary)' }}>
              选择实验想法
            </h2>
            <p className="text-xs truncate" style={{ color: 'var(--text-muted)', maxWidth: '420px' }}>
              来源：{sourceTitle}
            </p>
          </div>
          <button onClick={onCancel} className="text-xl leading-none mt-0.5"
            style={{ color: 'var(--text-muted)' }}>×</button>
        </div>

        {/* Toolbar */}
        <div className="px-6 py-2.5 border-b flex items-center justify-between"
          style={{ borderColor: 'var(--border-light)', backgroundColor: 'var(--bg-secondary)' }}>
          <button onClick={toggleAll} className="text-xs" style={{ color: 'var(--accent-blue)' }}>
            {selected.size === ideas.length ? '取消全选' : `全选 (${ideas.length})`}
          </button>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            已选 {selected.size} / {ideas.length} 个想法
          </span>
        </div>

        {/* Ideas list */}
        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-3">
          {ideas.map((idea, i) => {
            const isSelected = selected.has(i)
            return (
              <div key={i}
                onClick={() => toggle(i)}
                className="rounded-xl border cursor-pointer transition-all"
                style={{
                  borderColor: isSelected ? 'var(--accent-blue)' : 'var(--border)',
                  backgroundColor: isSelected ? '#eff6ff' : 'var(--bg-secondary)',
                  padding: '14px 16px',
                }}>
                <div className="flex items-start gap-3">
                  {/* Checkbox */}
                  <div className="mt-0.5 w-4 h-4 rounded border-2 flex-shrink-0 flex items-center justify-center"
                    style={{
                      borderColor: isSelected ? 'var(--accent-blue)' : 'var(--border)',
                      backgroundColor: isSelected ? 'var(--accent-blue)' : 'transparent',
                    }}>
                    {isSelected && <span className="text-white" style={{ fontSize: '10px', lineHeight: 1 }}>✓</span>}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {idea.title}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded-full font-medium"
                        style={{
                          color: DIFFICULTY_COLOR[idea.difficulty] || '#6b7280',
                          backgroundColor: (DIFFICULTY_COLOR[idea.difficulty] || '#6b7280') + '18',
                        }}>
                        {DIFFICULTY_LABEL[idea.difficulty] || idea.difficulty}
                      </span>
                      {idea.estimated_days && (
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                          ~{idea.estimated_days}天
                        </span>
                      )}
                    </div>
                    <p className="text-xs leading-relaxed mb-1" style={{ color: 'var(--text-secondary)' }}>
                      {idea.why}
                    </p>
                    {idea.value && (
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        价值：{idea.value}
                      </p>
                    )}
                    {(idea.tags || []).length > 0 && (
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {idea.tags.map(tag => (
                          <span key={tag} className="text-xs px-1.5 py-0.5 rounded"
                            style={{ backgroundColor: 'var(--border-light)', color: 'var(--text-muted)' }}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex items-center justify-end gap-3"
          style={{ borderColor: 'var(--border)' }}>
          <button onClick={onCancel} disabled={saving}
            className="text-sm px-4 py-2 rounded-lg border disabled:opacity-50"
            style={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}>
            取消
          </button>
          <button onClick={handleConfirm} disabled={selected.size === 0 || saving}
            className="text-sm px-5 py-2 rounded-lg font-medium disabled:opacity-40 transition-colors"
            style={{
              backgroundColor: selected.size > 0 ? 'var(--accent-blue)' : 'var(--border)',
              color: 'white',
            }}>
            {saving ? '保存中...' : `加入想法池 (${selected.size})`}
          </button>
        </div>
      </div>
    </div>
  )
}

const RDEV_TYPE_STYLE = {
  '研发提效': { color: '#2563eb', bg: '#dbeafe', icon: '🛠️' },
  '业务赋能': { color: '#d97706', bg: '#fef3c7', icon: '📈' },
}

const RDEV_DIFF_STYLE = {
  '低': { color: '#16a34a', bg: '#dcfce7' },
  '中': { color: '#d97706', bg: '#fef3c7' },
  '高': { color: '#dc2626', bg: '#fee2e2' },
}

function RdevScoreDot({ value }) {
  // score is 1-10, map to 5 dots (each dot = 2 points)
  const filled = Math.min(5, Math.max(0, Math.round(value / 2)))
  return (
    <div className="flex gap-0.5">
      {[1,2,3,4,5].map(i => (
        <span key={i} className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: i <= filled ? '#f59e0b' : '#e5e7eb' }} />
      ))}
    </div>
  )
}

function RdevPanel({ data, loading, onRefresh, onSearch, searching, remaining }) {
  const [current, setCurrent] = useState(0)
  const [saved, setSaved] = useState(new Set())
  const [skipped, setSkipped] = useState(new Set())

  const solutions = data?.solutions || []
  const topPick = data?.top_pick
  const total = solutions.length

  if (!loading && !data) return null

  const sol = solutions[current]
  const isTopPick = topPick && sol && topPick.title === sol.title
  const typeStyle = sol ? (RDEV_TYPE_STYLE[sol.type] || RDEV_TYPE_STYLE['研发提效']) : null
  const diffStyle = sol ? (RDEV_DIFF_STYLE[sol.difficulty] || RDEV_DIFF_STYLE['中']) : null

  async function handleSave() {
    if (!sol) return
    setSaved(prev => new Set([...prev, current]))
    try {
      const desc = [
        sol.scenario && `**痛点场景**\n${sol.scenario}`,
        sol.ai_solution && `**AI 切入点**\n${sol.ai_solution}`,
        sol.implementation && `**落地形态**\n${sol.implementation}`,
        sol.impact && `**预期收益**\n${sol.impact}`,
        sol.resistance && `**潜在阻力**\n${sol.resistance}`,
        isTopPick && topPick.mvp_path && `**今天第一步**\n${topPick.mvp_path}`,
        isTopPick && topPick.strategy && `**推进策略**\n${topPick.strategy}`,
      ].filter(Boolean).join('\n\n')
      await fetch('/api/experiments/ideas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: sol.title,
          description: desc,
          difficulty: sol.difficulty === '低' ? 'easy' : sol.difficulty === '高' ? 'hard' : 'medium',
          estimated_days: sol.difficulty === '低' ? 2 : sol.difficulty === '高' ? 14 : 7,
          tags: sol.audience || [],
          status: 'pending',
          priority: sol.scores?.overall || 0,
        })
      })
    } catch (e) {
      console.error('save rdev solution failed:', e)
    }
    if (current < total - 1) setCurrent(c => c + 1)
  }

  function handleSkip() {
    setSkipped(prev => new Set([...prev, current]))
    if (current < total - 1) setCurrent(c => c + 1)
  }

  return (
    <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            研发效能洞察
          </span>
          {!loading && total > 0 && (
            <span className="text-xs font-mono px-1.5 py-0.5 rounded"
              style={{ backgroundColor: '#fef3c7', color: '#d97706' }}>
              {total} 个方案
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {remaining !== 0 && (
            <button onClick={onSearch} disabled={searching || loading}
              className="text-xs px-3 py-1.5 rounded border font-medium transition-all"
              style={{
                color: '#d97706',
                borderColor: '#f59e0b',
                backgroundColor: searching ? '#fef3c7' : '#fffbeb',
                boxShadow: searching ? '0 0 0 2px #fde68a' : 'none',
              }}>
              {searching
                ? <span className="flex items-center gap-1.5">
                    <span style={{ animation: 'pulse 1s ease-in-out infinite' }}>●</span>
                    探索中...
                  </span>
                : '⊕ 探索机会'}
            </button>
          )}
          <button onClick={onRefresh} disabled={loading || searching}
            className="text-xs disabled:opacity-40" style={{ color: 'var(--text-muted)' }}>
            {loading ? '分析中...' : '↺ 重新分析'}
          </button>
        </div>
      </div>

      {searching && (
        <div className="rounded-xl border mb-3 overflow-hidden"
          style={{ borderColor: '#fde68a', backgroundColor: '#fffbeb' }}>
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <div className="flex items-center gap-2">
              {[0, 1, 2, 3, 4].map(i => (
                <span key={i} className="w-2 h-2 rounded-full"
                  style={{
                    backgroundColor: '#f59e0b',
                    animation: `pulse 1.2s ease-in-out ${i * 0.15}s infinite`,
                    opacity: 0.7,
                  }} />
              ))}
            </div>
            <p className="text-sm font-medium" style={{ color: '#92400e' }}>AI 正在探索更多研发效能机会...</p>
            <p className="text-xs" style={{ color: '#b45309' }}>分析未覆盖情报，约需 20-40 秒</p>
          </div>
        </div>
      )}

      {loading && !data ? (
        <div className="flex items-center gap-2 py-6 justify-center text-sm" style={{ color: 'var(--text-muted)' }}>
          <span className="loading-pulse">▌</span>
          <span>AI 正在扫描研发效能机会，约需 20-30 秒...</span>
        </div>
      ) : sol ? (
        <div className="flex items-start gap-4">
          {/* Card */}
          <div className="flex-1 rounded-xl border overflow-hidden"
            style={{ backgroundColor: 'white', borderColor: isTopPick ? '#fbbf24' : 'var(--border)' }}>
            {/* Card header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b"
              style={{
                backgroundColor: isTopPick ? '#fef3c7' : 'var(--bg-secondary)',
                borderColor: isTopPick ? '#fde68a' : 'var(--border)',
              }}>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{ backgroundColor: typeStyle.bg, color: typeStyle.color }}>
                  {typeStyle.icon} {sol.type}
                </span>
                {isTopPick && (
                  <span className="text-xs font-semibold" style={{ color: '#92400e' }}>⭐ 今日优先</span>
                )}
                {sol.trigger && (
                  sol.source_url
                    ? <a href={sol.source_url} target="_blank" rel="noopener noreferrer"
                        className="text-xs truncate max-w-xs hover:underline"
                        style={{ color: 'var(--accent-blue)' }}>
                        📡 {sol.trigger}
                      </a>
                    : <span className="text-xs truncate max-w-xs" style={{ color: 'var(--text-muted)' }}>
                        📡 {sol.trigger}
                      </span>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                {saved.has(current) && (
                  <span className="text-xs px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: '#dcfce7', color: '#16a34a' }}>✓ 已记录</span>
                )}
                <span className="text-xs px-1.5 py-0.5 rounded"
                  style={{ backgroundColor: diffStyle.bg, color: diffStyle.color }}>
                  {sol.difficulty}难度
                </span>
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                  {current + 1} / {total}
                </span>
              </div>
            </div>

            {/* Card body */}
            <div className="p-4 space-y-3 text-sm">
              <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                {sol.title}
              </h3>

              {sol.ai_solution && (
                <div className="p-3 rounded-lg" style={{ backgroundColor: '#eff6ff', borderLeft: '3px solid #3b82f6' }}>
                  <span className="text-xs font-semibold" style={{ color: '#2563eb' }}>🧠 AI 切入点</span>
                  <p className="mt-1 text-xs leading-relaxed" style={{ color: '#1e40af' }}>{sol.ai_solution}</p>
                </div>
              )}

              {sol.scenario && (
                <div>
                  <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>🎯 痛点场景</span>
                  <p className="mt-0.5 text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{sol.scenario}</p>
                </div>
              )}

              {sol.implementation && (
                <div>
                  <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>⚙️ 落地形态</span>
                  <p className="mt-0.5 text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{sol.implementation}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                {sol.impact && (
                  <div className="p-2 rounded text-xs" style={{ backgroundColor: '#f0fdf4' }}>
                    <span className="font-semibold" style={{ color: '#16a34a' }}>📊 预期收益</span>
                    <p className="mt-0.5" style={{ color: '#15803d' }}>{sol.impact}</p>
                  </div>
                )}
                {sol.resistance && (
                  <div className="p-2 rounded text-xs" style={{ backgroundColor: '#fff7ed' }}>
                    <span className="font-semibold" style={{ color: '#ea580c' }}>🚧 潜在阻力</span>
                    <p className="mt-0.5" style={{ color: '#c2410c' }}>{sol.resistance}</p>
                  </div>
                )}
              </div>

              {/* top_pick action box */}
              {isTopPick && topPick && (
                <div className="p-3 rounded-lg border" style={{ backgroundColor: '#fffbeb', borderColor: '#fde68a' }}>
                  {topPick.mvp_path && (
                    <p className="text-xs mb-1" style={{ color: '#92400e' }}>
                      <span className="font-semibold">今天第一步：</span>{topPick.mvp_path}
                    </p>
                  )}
                  {topPick.strategy && (
                    <p className="text-xs" style={{ color: '#b45309' }}>
                      <span className="font-semibold">推进策略：</span>{topPick.strategy}
                    </p>
                  )}
                </div>
              )}

              {/* Scores */}
              {sol.scores && (
                <div className="mt-1 pt-3 border-t grid grid-cols-4 gap-2"
                  style={{ borderColor: 'var(--border-light)' }}>
                  {[
                    { key: 'efficiency', label: '提效' },
                    { key: 'feasibility', label: '可行' },
                    { key: 'business_impact', label: '影响' },
                    { key: 'overall', label: '综合' },
                  ].map(({ key, label }) => (
                    <div key={key} className="flex flex-col gap-1 items-center">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
                      <RdevScoreDot value={sol.scores[key] || 0} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Card footer */}
            <div className="flex border-t" style={{ borderColor: 'var(--border)' }}>
              <button onClick={handleSkip}
                className="flex-1 py-2.5 text-sm font-medium transition-colors hover:bg-red-50"
                style={{ color: '#dc2626', borderRight: '1px solid var(--border)' }}>
                ✕ 跳过
              </button>
              <button onClick={handleSave} disabled={saved.has(current)}
                className="flex-1 py-2.5 text-sm font-medium transition-colors hover:bg-amber-50 disabled:opacity-50"
                style={{ color: '#d97706' }}>
                ♥ 记录行动项
              </button>
            </div>
          </div>

          {/* Side navigation */}
          <div className="flex flex-col gap-2 justify-center pt-16">
            <button onClick={() => setCurrent(c => Math.max(0, c - 1))}
              disabled={current === 0}
              className="w-8 h-8 rounded-full border flex items-center justify-center text-sm disabled:opacity-30 hover:bg-gray-50"
              style={{ borderColor: 'var(--border)' }}>‹</button>
            <button onClick={() => setCurrent(c => Math.min(total - 1, c + 1))}
              disabled={current === total - 1}
              className="w-8 h-8 rounded-full border flex items-center justify-center text-sm disabled:opacity-30 hover:bg-gray-50"
              style={{ borderColor: 'var(--border)' }}>›</button>
          </div>
        </div>
      ) : null}

      {/* Progress dots */}
      {total > 0 && (
        <div className="flex gap-1 mt-3 justify-center flex-wrap">
          {solutions.map((s, i) => {
            const isTP = topPick && topPick.title === s.title
            return (
              <button key={i} onClick={() => setCurrent(i)}
                className="w-2 h-2 rounded-full transition-all"
                style={{
                  backgroundColor: i === current ? '#f59e0b'
                    : saved.has(i) ? '#16a34a'
                    : skipped.has(i) ? '#d1d5db'
                    : isTP ? '#fbbf24'
                    : '#cbd5e1'
                }} />
            )
          })}
        </div>
      )}
    </div>
  )
}

export default BriefingPage
