import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'

const PLATFORMS = ['X', 'Reddit', 'Blog', 'HackerNews', 'other']

const PLATFORM_BADGES = {
  X:          { label: '𝕏',          style: { background: '#f0f0f0', color: '#333' } },
  Reddit:     { label: 'Reddit',     style: { background: '#fff0eb', color: '#c0392b' } },
  Blog:       { label: 'Blog',       style: { background: '#eef2ff', color: '#4338ca' } },
  HackerNews: { label: 'HN',         style: { background: '#fff7ed', color: '#c2410c' } },
  other:      { label: '其他',        style: { background: '#f3f4f6', color: '#6b7280' } },
}

function Badge({ platform }) {
  const cfg = PLATFORM_BADGES[platform] || PLATFORM_BADGES.other
  return (
    <span style={{
      fontSize: 11, padding: '2px 7px', borderRadius: 4, fontWeight: 500, ...cfg.style
    }}>{cfg.label}</span>
  )
}

function CollapsibleSection({ icon, title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 7, overflow: 'hidden' }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '8px 12px', background: 'var(--bg-secondary)', cursor: 'pointer',
          fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)',
        }}
      >
        <span>{icon} {title}</span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ padding: '10px 12px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          {children}
        </div>
      )}
    </div>
  )
}

function OpportunityCard({ opp }) {
  return (
    <div style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{opp.opportunity_title}</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>{opp.core_insight}</div>
      <div style={{ fontSize: 12 }}><strong>产品形态：</strong>{opp.product_form}</div>
      <div style={{ fontSize: 12 }}><strong>目标用户：</strong>{opp.target_users}</div>
      {opp.mvp_features?.length > 0 && (
        <div style={{ fontSize: 12, marginTop: 4 }}>
          <strong>MVP 功能：</strong>{opp.mvp_features.join(' · ')}
        </div>
      )}
      <div style={{ fontSize: 12 }}><strong>商业模式：</strong>{opp.business_model}</div>
      <div style={{ fontSize: 12, color: '#dc2626' }}><strong>风险：</strong>{opp.risks}</div>
    </div>
  )
}

function RdevCard({ sol }) {
  return (
    <div style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 11, padding: '2px 6px', borderRadius: 4, background: '#f0fdf4', color: '#15803d' }}>
          {sol.type}
        </span>
        <span style={{ fontWeight: 600, fontSize: 13 }}>{sol.title}</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>难度：{sol.difficulty}</span>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 2 }}>{sol.scenario}</div>
      <div style={{ fontSize: 12 }}><strong>方案：</strong>{sol.ai_solution}</div>
      <div style={{ fontSize: 12 }}><strong>落地形态：</strong>{sol.implementation}</div>
      <div style={{ fontSize: 12, color: '#2563eb' }}><strong>预期收益：</strong>{sol.impact}</div>
    </div>
  )
}

function ItemCard({ item, onDelete, onReanalyze }) {
  const isAnalyzing = !item.quick_read && !item.business_opps?.length && !item.rdev_opps?.length

  return (
    <div style={{
      background: 'var(--bg-primary)', borderRadius: 10, border: '1px solid var(--border)',
      padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <a
            href={item.url} target="_blank" rel="noreferrer"
            style={{ fontSize: 14, fontWeight: 600, color: 'var(--accent)', textDecoration: 'none', lineHeight: 1.4 }}
          >
            {item.title || item.url}
          </a>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            <Badge platform={item.source_platform} />
            <span style={{
              fontSize: 10, padding: '2px 6px', borderRadius: 4, border: '1px solid #bbf7d0',
              background: '#f0fdf4', color: '#15803d',
            }}>手动录入</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {new Date(item.added_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, marginLeft: 12 }}>
          <button
            onClick={() => onReanalyze(item.id)}
            style={{ fontSize: 11, padding: '4px 8px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer', color: 'var(--text-secondary)' }}
          >重新分析</button>
          <button
            onClick={() => onDelete(item.id)}
            style={{ fontSize: 11, padding: '4px 8px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer', color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#fca5a5'; e.currentTarget.style.color = '#dc2626' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
          >删除</button>
        </div>
      </div>

      {/* User note */}
      {item.user_note && (
        <div style={{
          fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-secondary)',
          borderRadius: 5, padding: '6px 10px', marginBottom: 10, fontStyle: 'italic',
        }}>
          💬 {item.user_note}
        </div>
      )}

      {/* Analysis sections */}
      {isAnalyzing ? (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 0' }}>⏳ AI 分析中，请稍候…</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <CollapsibleSection icon="⚡" title="速读摘要" defaultOpen={true}>
            {item.quick_read
              ? <ReactMarkdown>{item.quick_read}</ReactMarkdown>
              : <span style={{ color: 'var(--text-muted)' }}>暂无速读</span>}
          </CollapsibleSection>

          <CollapsibleSection icon="💼" title={`商业机会${item.business_opps?.length ? ` (${item.business_opps.length})` : ''}`}>
            {item.business_opps?.length
              ? item.business_opps.map((opp, i) => <OpportunityCard key={i} opp={opp} />)
              : <span style={{ color: 'var(--text-muted)' }}>未发现明显商业机会</span>}
          </CollapsibleSection>

          <CollapsibleSection icon="🔬" title={`研发机会${item.rdev_opps?.length ? ` (${item.rdev_opps.length})` : ''}`}>
            {item.rdev_opps?.length
              ? item.rdev_opps.map((sol, i) => <RdevCard key={i} sol={sol} />)
              : <span style={{ color: 'var(--text-muted)' }}>未发现研发落地机会</span>}
          </CollapsibleSection>
        </div>
      )}
    </div>
  )
}

export default function ManualIntelPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [platformFilter, setPlatformFilter] = useState('all')
  const [url, setUrl] = useState('')
  const [platform, setPlatform] = useState('other')
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const pollingRef = useRef({}) // { [item_id]: intervalId }

  const fetchItems = useCallback(async () => {
    try {
      const resp = await fetch('/api/manual-intel')
      const data = await resp.json()
      setItems(data.items || [])
    } catch (e) {
      console.error('Failed to fetch manual intel items', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchItems()
    return () => {
      Object.values(pollingRef.current).forEach(clearInterval)
    }
  }, [fetchItems])

  const startPolling = useCallback((itemId) => {
    if (pollingRef.current[itemId]) return
    pollingRef.current[itemId] = setInterval(async () => {
      try {
        const resp = await fetch(`/api/manual-intel/${itemId}`)
        if (!resp.ok) return
        const updated = await resp.json()
        const done = updated.quick_read !== '' ||
                     (Array.isArray(updated.business_opps) && updated.business_opps.length > 0) ||
                     (Array.isArray(updated.rdev_opps) && updated.rdev_opps.length > 0)
        setItems(prev => prev.map(i => i.id === itemId ? updated : i))
        if (done) {
          clearInterval(pollingRef.current[itemId])
          delete pollingRef.current[itemId]
        }
      } catch (e) {
        // keep polling
      }
    }, 3000)
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return
    setSubmitting(true)
    setSubmitError('')
    try {
      const resp = await fetch('/api/manual-intel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim(), source_platform: platform, user_note: note.trim() }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        setSubmitError(err.detail || '录入失败')
        return
      }
      const newItem = await resp.json()
      setItems(prev => [newItem, ...prev])
      startPolling(newItem.id)
      setUrl('')
      setNote('')
      setPlatform('other')
    } catch (e) {
      setSubmitError('网络错误，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(itemId) {
    await fetch(`/api/manual-intel/${itemId}`, { method: 'DELETE' })
    if (pollingRef.current[itemId]) {
      clearInterval(pollingRef.current[itemId])
      delete pollingRef.current[itemId]
    }
    setItems(prev => prev.filter(i => i.id !== itemId))
  }

  async function handleReanalyze(itemId) {
    await fetch(`/api/manual-intel/${itemId}/reanalyze`, { method: 'POST' })
    setItems(prev => prev.map(i => i.id === itemId
      ? { ...i, quick_read: '', business_opps: [], rdev_opps: [] }
      : i
    ))
    startPolling(itemId)
  }

  const filtered = platformFilter === 'all'
    ? items
    : items.filter(i => i.source_platform === platformFilter)

  const usedPlatforms = [...new Set(items.map(i => i.source_platform).filter(Boolean))]

  return (
    <div>
      {/* Page header */}
      <div style={{ padding: '20px 28px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg-primary)' }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
          📌 我的情报收藏
          <span style={{ fontSize: 12, background: 'var(--bg-secondary)', color: 'var(--text-muted)', borderRadius: 10, padding: '2px 8px' }}>
            {items.length}
          </span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>手动录入的情报，自动生成速读与机会分析</p>
      </div>

      {/* Input form */}
      <div style={{ margin: '16px 28px', background: 'var(--bg-primary)', borderRadius: 10, border: '1px solid var(--border)', padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <input
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="粘贴文章链接…"
              required
              style={{
                flex: 1, border: '1.5px solid var(--border)', borderRadius: 6,
                padding: '9px 12px', fontSize: 13, color: 'var(--text-primary)',
                background: 'var(--bg-secondary)', outline: 'none',
              }}
            />
            <select
              value={platform}
              onChange={e => setPlatform(e.target.value)}
              style={{
                border: '1.5px solid var(--border)', borderRadius: 6,
                padding: '9px 10px', fontSize: 13, background: 'var(--bg-secondary)',
                color: 'var(--text-primary)', width: 130,
              }}
            >
              {PLATFORMS.map(p => (
                <option key={p} value={p}>{p === 'X' ? '𝕏 (Twitter)' : p}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={submitting}
              style={{
                background: submitting ? '#93c5fd' : '#1a56db', color: '#fff',
                border: 'none', borderRadius: 6, padding: '9px 16px',
                fontSize: 13, fontWeight: 500, cursor: submitting ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
              }}
            >
              {submitting ? '录入中…' : '+ 录入情报'}
            </button>
          </div>
          <textarea
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="添加点评（可选）：为什么觉得这条内容值得收藏？"
            rows={2}
            style={{
              width: '100%', border: '1.5px solid var(--border)', borderRadius: 6,
              padding: '8px 12px', fontSize: 12, color: 'var(--text-secondary)',
              background: 'var(--bg-secondary)', resize: 'none', fontFamily: 'inherit',
            }}
          />
          {submitError && <p style={{ fontSize: 12, color: '#dc2626', marginTop: 6 }}>{submitError}</p>}
        </form>
      </div>

      {/* Platform filter chips */}
      {usedPlatforms.length > 1 && (
        <div style={{ display: 'flex', gap: 6, padding: '0 28px 12px', flexWrap: 'wrap' }}>
          {['all', ...usedPlatforms].map(p => (
            <button
              key={p}
              onClick={() => setPlatformFilter(p)}
              style={{
                fontSize: 12, padding: '4px 12px', borderRadius: 20,
                border: '1px solid var(--border)', cursor: 'pointer',
                background: platformFilter === p ? '#1a56db' : 'var(--bg-primary)',
                color: platformFilter === p ? '#fff' : 'var(--text-secondary)',
                borderColor: platformFilter === p ? '#1a56db' : 'var(--border)',
              }}
            >
              {p === 'all' ? '全部' : p}
            </button>
          ))}
        </div>
      )}

      {/* Items list */}
      <div style={{ padding: '0 28px 28px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)', fontSize: 14 }}>加载中…</div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)', fontSize: 14 }}>
            还没有情报，粘贴一个链接试试 👆
          </div>
        ) : (
          filtered.map(item => (
            <ItemCard
              key={item.id}
              item={item}
              onDelete={handleDelete}
              onReanalyze={handleReanalyze}
            />
          ))
        )}
      </div>
    </div>
  )
}
