import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'

const PLATFORMS = ['X', 'Reddit', 'Blog', 'HackerNews', 'other']

const PLATFORM_BADGES = {
  X:          { label: '𝕏',      style: { background: '#f0f0f0', color: '#333' } },
  Reddit:     { label: 'Reddit', style: { background: '#fff0eb', color: '#c0392b' } },
  Blog:       { label: 'Blog',   style: { background: '#eef2ff', color: '#4338ca' } },
  HackerNews: { label: 'HN',     style: { background: '#fff7ed', color: '#c2410c' } },
  other:      { label: '其他',   style: { background: '#f3f4f6', color: '#6b7280' } },
}

const DIFFICULTY_LABEL = { easy: '简单', medium: '中等', hard: '困难' }
const DIFFICULTY_COLOR = { easy: '#16a34a', medium: '#d97706', hard: '#dc2626' }

function PlatformBadge({ platform }) {
  const cfg = PLATFORM_BADGES[platform] || PLATFORM_BADGES.other
  return (
    <span style={{ fontSize: 11, padding: '2px 7px', borderRadius: 4, fontWeight: 500, ...cfg.style }}>
      {cfg.label}
    </span>
  )
}

function CollapsibleSection({ icon, title, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '7px 12px', background: 'var(--bg-secondary)', cursor: 'pointer',
          fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)',
        }}
      >
        <span>{icon} {title}</span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ padding: '4px 16px 4px' }}>
          {children}
        </div>
      )}
    </div>
  )
}

const SERIF = 'ui-serif, Georgia, Cambria, "Times New Roman", serif'
const PROSE_COLOR = '#111827'

function ProseField({ label, value, color }) {
  if (!value) return null
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 3 }}>
        {label}
      </div>
      <div style={{ fontFamily: SERIF, fontSize: 14, color: color || PROSE_COLOR, lineHeight: 1.7 }}>
        {value}
      </div>
    </div>
  )
}

function OpportunityCard({ opp }) {
  return (
    <div style={{ padding: '16px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 16, color: PROSE_COLOR, marginBottom: 6, lineHeight: 1.4 }}>
        {opp.opportunity_title}
      </div>
      {opp.core_insight && (
        <div style={{ fontFamily: SERIF, fontSize: 14, color: '#374151', lineHeight: 1.7, marginBottom: 12, fontStyle: 'italic' }}>
          {opp.core_insight}
        </div>
      )}
      <ProseField label="产品形态" value={opp.product_form} />
      <ProseField label="目标用户" value={opp.target_users} />
      {opp.mvp_features?.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 3 }}>
            MVP 功能
          </div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {opp.mvp_features.map((f, i) => (
              <li key={i} style={{ fontFamily: SERIF, fontSize: 14, color: PROSE_COLOR, lineHeight: 1.7 }}>{f}</li>
            ))}
          </ul>
        </div>
      )}
      <ProseField label="商业模式" value={opp.business_model} />
      {opp.risks && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 3 }}>
            风险
          </div>
          <div style={{ fontFamily: SERIF, fontSize: 14, color: '#b91c1c', lineHeight: 1.7 }}>{opp.risks}</div>
        </div>
      )}
    </div>
  )
}

function RdevCard({ sol }) {
  return (
    <div style={{ padding: '16px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20, background: '#dbeafe', color: '#1d4ed8', fontWeight: 500 }}>
          {sol.type}
        </span>
        <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20, background: '#f3f4f6', color: '#6b7280', fontWeight: 500 }}>
          {sol.difficulty}难度
        </span>
      </div>
      <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 16, color: PROSE_COLOR, marginBottom: 6, lineHeight: 1.4 }}>
        {sol.title}
      </div>
      {sol.scenario && (
        <div style={{ fontFamily: SERIF, fontSize: 14, color: '#374151', lineHeight: 1.7, marginBottom: 12, fontStyle: 'italic' }}>
          {sol.scenario}
        </div>
      )}
      <ProseField label="AI 切入点" value={sol.ai_solution} />
      <ProseField label="落地形态" value={sol.implementation} />
      {sol.impact && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 3 }}>
            预期收益
          </div>
          <div style={{ fontFamily: SERIF, fontSize: 14, color: '#1d4ed8', lineHeight: 1.7 }}>{sol.impact}</div>
        </div>
      )}
    </div>
  )
}

function GenerateBtn({ loading, label, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        fontSize: 12, padding: '6px 14px', borderRadius: 6, textAlign: 'left',
        border: '1px solid var(--border)', cursor: loading ? 'not-allowed' : 'pointer',
        background: 'var(--bg-secondary)',
        color: loading ? 'var(--text-muted)' : 'var(--text-secondary)',
      }}
    >
      {loading ? '⏳ 生成中…' : label}
    </button>
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
      boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
    }}>
      <div style={{ fontSize: 12, marginBottom: 8, color: 'var(--text-muted)' }}>
        ✏️ 输入你的想法方向（可选）
      </div>
      <textarea
        autoFocus
        value={hint}
        onChange={e => setHint(e.target.value)}
        placeholder="例如：想探索 agent 工具调用的边界…"
        rows={2}
        style={{
          width: '100%', fontSize: 12, borderRadius: 4, padding: '6px 8px', resize: 'none',
          border: '1px solid var(--border)', background: 'var(--bg-secondary)',
          color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
        }}
      />
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button
          onClick={() => onGenerate(hint)}
          style={{
            flex: 1, fontSize: 12, padding: '6px 0', borderRadius: 5,
            border: '1px solid var(--accent-purple, #a78bfa)',
            color: 'var(--accent-purple, #a78bfa)', background: 'transparent', cursor: 'pointer',
          }}
        >引导生成</button>
        <button
          onClick={() => onGenerate('')}
          style={{
            flex: 1, fontSize: 12, padding: '6px 0', borderRadius: 5,
            border: '1px solid var(--border)',
            color: 'var(--text-muted)', background: 'transparent', cursor: 'pointer',
          }}
        >直接生成</button>
      </div>
    </div>
  )
}

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
    <div
      style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, backgroundColor: 'rgba(0,0,0,0.5)' }}
      onClick={e => e.target === e.currentTarget && onCancel()}
    >
      <div style={{
        width: '100%', maxWidth: 560, borderRadius: 16, overflow: 'hidden',
        backgroundColor: 'var(--bg-primary)', maxHeight: '85vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 24px 48px rgba(0,0,0,0.3)',
      }}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 2, color: 'var(--text-primary)' }}>选择实验想法</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 400 }}>
              来源：{sourceTitle}
            </div>
          </div>
          <button onClick={onCancel} style={{ fontSize: 20, lineHeight: 1, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
        </div>

        <div style={{ padding: '8px 24px', borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button onClick={toggleAll} style={{ fontSize: 12, color: 'var(--accent-blue)', background: 'none', border: 'none', cursor: 'pointer' }}>
            {selected.size === ideas.length ? '取消全选' : `全选 (${ideas.length})`}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>已选 {selected.size} / {ideas.length} 个想法</span>
        </div>

        <div style={{ overflowY: 'auto', flex: 1, padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {ideas.map((idea, i) => {
            const isSelected = selected.has(i)
            return (
              <div
                key={i}
                onClick={() => toggle(i)}
                style={{
                  borderRadius: 12, border: `1px solid ${isSelected ? 'var(--accent-blue)' : 'var(--border)'}`,
                  backgroundColor: isSelected ? '#eff6ff' : 'var(--bg-secondary)',
                  padding: '14px 16px', cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{
                    marginTop: 2, width: 16, height: 16, borderRadius: 3, flexShrink: 0,
                    border: `2px solid ${isSelected ? 'var(--accent-blue)' : 'var(--border)'}`,
                    backgroundColor: isSelected ? 'var(--accent-blue)' : 'transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {isSelected && <span style={{ color: 'white', fontSize: 10, lineHeight: 1 }}>✓</span>}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{idea.title}</span>
                      <span style={{
                        fontSize: 11, padding: '2px 6px', borderRadius: 20, fontWeight: 500,
                        color: DIFFICULTY_COLOR[idea.difficulty] || '#6b7280',
                        backgroundColor: (DIFFICULTY_COLOR[idea.difficulty] || '#6b7280') + '18',
                      }}>
                        {DIFFICULTY_LABEL[idea.difficulty] || idea.difficulty}
                      </span>
                      {idea.estimated_days && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>~{idea.estimated_days}天</span>
                      )}
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 4 }}>{idea.why}</p>
                    {idea.value && (
                      <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>价值：{idea.value}</p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
          <button onClick={onCancel} disabled={saving} style={{ fontSize: 13, padding: '7px 16px', borderRadius: 8, border: '1px solid var(--border)', color: 'var(--text-secondary)', background: 'none', cursor: 'pointer' }}>
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={selected.size === 0 || saving}
            style={{
              fontSize: 13, padding: '7px 20px', borderRadius: 8, fontWeight: 500,
              backgroundColor: selected.size > 0 ? 'var(--accent-blue)' : 'var(--border)',
              color: 'white', border: 'none', cursor: selected.size > 0 ? 'pointer' : 'default',
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? '保存中...' : `加入想法池 (${selected.size})`}
          </button>
        </div>
      </div>
    </div>
  )
}

function ItemCard({ item, onDelete, onReanalyze, onUpdateItem, selected, onToggle }) {
  const [quickReadCollapsed, setQuickReadCollapsed] = useState(false)
  const [businessLoading, setBusinessLoading] = useState(false)
  const [rdevLoading, setRdevLoading] = useState(false)
  const [genState, setGenState] = useState('idle') // idle | loading | done | error
  const [genError, setGenError] = useState('')
  const [generatedIdeas, setGeneratedIdeas] = useState(null)
  const [savedCount, setSavedCount] = useState(0)
  const [popoverOpen, setPopoverOpen] = useState(false)
  const closePopover = useCallback(() => setPopoverOpen(false), [])

  const isAnalyzingQuickRead = !item.quick_read

  async function handleGenerateBusiness() {
    setBusinessLoading(true)
    try {
      const resp = await fetch(`/api/manual-intel/${item.id}/generate-business`, { method: 'POST' })
      if (resp.ok) {
        const data = await resp.json()
        onUpdateItem(item.id, { business_opps: data.business_opps })
      }
    } catch (e) {
      console.error('generate-business failed', e)
    } finally {
      setBusinessLoading(false)
    }
  }

  async function handleGenerateRdev() {
    setRdevLoading(true)
    try {
      const resp = await fetch(`/api/manual-intel/${item.id}/generate-rdev`, { method: 'POST' })
      if (resp.ok) {
        const data = await resp.json()
        onUpdateItem(item.id, { rdev_opps: data.rdev_opps })
      }
    } catch (e) {
      console.error('generate-rdev failed', e)
    } finally {
      setRdevLoading(false)
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
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setGeneratedIdeas(data.ideas || [])
      setGenState('selecting')
    } catch (e) {
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
          priority: 0,
          source_type: 'manual_intel',
          source_title: item.title || '',
          source_url: item.url || '',
        })
      })
    ))
    setSavedCount(selectedIdeas.length)
    setGeneratedIdeas(null)
    setGenState('done')
  }

  return (
    <article className="content-card" style={selected ? { outline: '1px solid #2563eb', outlineOffset: '-1px' } : {}}>
      {/* Card header */}
      <div className="card-header">
        <button
          onClick={() => item.quick_read && onToggle?.()}
          title={!item.quick_read ? '需先生成速读才能加入分享' : (selected ? '取消选择' : '加入分享文案')}
          style={{
            width: 16, height: 16, borderRadius: 3, flexShrink: 0,
            border: `1.5px solid ${selected ? '#2563eb' : item.quick_read ? '#4b5563' : '#1f2937'}`,
            background: selected ? '#2563eb' : 'transparent',
            color: 'white', fontSize: 9,
            cursor: item.quick_read ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 0,
          }}
        >
          {selected && '✓'}
        </button>
        <PlatformBadge platform={item.source_platform} />
        <span style={{
          fontSize: 11, padding: '2px 6px', borderRadius: 4,
          border: '1px solid #bbf7d0', background: '#f0fdf4', color: '#15803d',
        }}>手动录入</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
          {new Date(item.added_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
        </span>
        <a
          href={item.url} target="_blank" rel="noreferrer"
          style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--accent-blue)', textDecoration: 'none' }}
        >
          原文 →
        </a>
      </div>

      <div style={{ padding: '14px 16px 16px' }}>
        {/* Title */}
        <h3 style={{
          fontFamily: 'monospace', fontWeight: 700, fontSize: 15,
          marginBottom: item.user_note ? 8 : 12,
          color: 'var(--text-primary)', lineHeight: 1.4,
        }}>
          {item.title || item.url}
        </h3>

        {/* User note */}
        {item.user_note && (
          <div style={{
            fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-secondary)',
            borderRadius: 5, padding: '6px 10px', marginBottom: 12, fontStyle: 'italic',
          }}>
            💬 {item.user_note}
          </div>
        )}

        {/* Quick read section */}
        {isAnalyzingQuickRead ? (
          <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 0', marginBottom: 12 }}>
            ⏳ 速读生成中…
          </div>
        ) : item.quick_read && !quickReadCollapsed ? (
          <div style={{
            marginBottom: 12, padding: '14px 16px', borderRadius: 8,
            background: '#f0fdf4', borderLeft: '2px solid #22c55e',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
              <span style={{ fontSize: 12 }}>⚡</span>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#16a34a' }}>速读摘要</span>
            </div>
            <div className="markdown-content manual-intel-prose" style={{ fontFamily: SERIF, fontSize: 15, color: PROSE_COLOR, lineHeight: 1.8 }}>
              <ReactMarkdown>{item.quick_read}</ReactMarkdown>
            </div>
          </div>
        ) : null}

        {/* Business and Rdev — only after quick_read is ready */}
        {item.quick_read && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
            {item.business_opps?.length > 0 ? (
              <CollapsibleSection icon="💼" title={`商业机会 (${item.business_opps.length})`}>
                {item.business_opps.map((opp, i) => <OpportunityCard key={i} opp={opp} />)}
              </CollapsibleSection>
            ) : (
              <GenerateBtn loading={businessLoading} label="💼 生成商业机会" onClick={handleGenerateBusiness} />
            )}

            {item.rdev_opps?.length > 0 ? (
              <CollapsibleSection icon="🔬" title={`研发机会 (${item.rdev_opps.length})`}>
                {item.rdev_opps.map((sol, i) => <RdevCard key={i} sol={sol} />)}
              </CollapsibleSection>
            ) : (
              <GenerateBtn loading={rdevLoading} label="🔬 生成研发机会" onClick={handleGenerateRdev} />
            )}
          </div>
        )}

        {/* Footer actions */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          paddingTop: 10, borderTop: '1px solid var(--border)', marginTop: 4,
        }}>
          {/* Left: management actions */}
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => onReanalyze(item.id)}
              style={{
                fontSize: 11, padding: '3px 8px', borderRadius: 5,
                border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                cursor: 'pointer', color: 'var(--text-secondary)',
              }}
            >重新速读</button>
            <button
              onClick={() => onDelete(item.id)}
              style={{
                fontSize: 11, padding: '3px 8px', borderRadius: 5,
                border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                cursor: 'pointer', color: 'var(--text-secondary)',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#fca5a5'; e.currentTarget.style.color = '#dc2626' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
            >删除</button>
          </div>

          {/* Right: content actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {item.quick_read && (
              <button
                onClick={() => setQuickReadCollapsed(c => !c)}
                style={{
                  fontSize: 12, padding: '3px 8px', borderRadius: 5,
                  border: '1px solid #86efac', background: '#f0fdf4',
                  color: '#16a34a', cursor: 'pointer',
                }}
              >
                {quickReadCollapsed ? '⚡ 展开速读' : '⚡ 收起速读'}
              </button>
            )}

            {/* Generate ideas split button */}
            {genState === 'done' ? (
              <span style={{ fontSize: 12, color: 'var(--accent-green)', padding: '3px 8px' }}>
                已保存 {savedCount} 个想法
              </span>
            ) : (
              <div style={{ position: 'relative' }}>
                <div style={{ display: 'flex', border: '1px solid var(--border)', borderRadius: 5 }}>
                  <button
                    onClick={genState === 'error' ? () => setGenState('idle') : () => generateIdeas('')}
                    disabled={genState === 'loading' || genState === 'selecting'}
                    title={genState === 'error' ? genError : ''}
                    style={{
                      fontSize: 12, padding: '3px 8px',
                      color: genState === 'error' ? '#dc2626' : 'var(--text-muted)',
                      borderRight: '1px solid var(--border)',
                      background: 'transparent', border: 'none',
                      borderRight: '1px solid var(--border)',
                      cursor: genState === 'loading' || genState === 'selecting' ? 'not-allowed' : 'pointer',
                      opacity: genState === 'loading' || genState === 'selecting' ? 0.5 : 1,
                    }}
                  >
                    {genState === 'loading' ? '⏳ 生成中...'
                      : genState === 'error' ? '生成失败（重试）'
                      : '生成实验想法'}
                  </button>
                  <button
                    onClick={() => setPopoverOpen(o => !o)}
                    disabled={genState === 'loading' || genState === 'selecting' || genState === 'error'}
                    style={{
                      fontSize: 11, padding: '3px 6px',
                      color: popoverOpen ? 'var(--accent-purple, #a78bfa)' : 'var(--text-muted)',
                      background: popoverOpen ? 'rgba(167,139,250,0.08)' : 'transparent',
                      border: 'none', cursor: 'pointer',
                      opacity: genState === 'loading' || genState === 'selecting' || genState === 'error' ? 0.3 : 1,
                    }}
                  >▲</button>
                </div>
                {popoverOpen && (
                  <GuidedIdeaPopover onGenerate={generateIdeas} onClose={closePopover} />
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Ideas select modal */}
      {genState === 'selecting' && generatedIdeas && (
        <IdeasSelectModal
          ideas={generatedIdeas}
          sourceTitle={item.title || item.url}
          onConfirm={saveSelectedIdeas}
          onCancel={() => { setGeneratedIdeas(null); setGenState('idle') }}
        />
      )}
    </article>
  )
}

function ShareBar({ count, onClear, onGenerate, generating }) {
  if (count === 0) return null
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '6px 0', marginTop: 6, fontSize: 12,
    }}>
      <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
        已选 <strong style={{ color: 'var(--text-primary)' }}>{count} 条情报</strong>
      </span>
      <span style={{ flex: 1 }} />
      <button
        onClick={onClear}
        disabled={generating}
        style={{
          background: 'transparent', border: '1px solid var(--border)',
          color: 'var(--text-muted)', padding: '3px 10px', borderRadius: 5,
          fontSize: 11, cursor: 'pointer',
        }}
      >清空</button>
      <button
        onClick={onGenerate}
        disabled={generating || count === 0}
        style={{
          background: '#9a3412', border: 'none', color: 'white',
          padding: '3px 12px', borderRadius: 5, fontSize: 11,
          fontWeight: 600, cursor: generating ? 'default' : 'pointer',
          opacity: generating ? 0.6 : 1,
        }}
      >
        {generating ? '生成中...' : '生成分享页 →'}
      </button>
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
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [generating, setGenerating] = useState(false)
  const pollingRef = useRef({})

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
    return () => { Object.values(pollingRef.current).forEach(clearInterval) }
  }, [fetchItems])

  const startPolling = useCallback((itemId) => {
    if (pollingRef.current[itemId]) return
    pollingRef.current[itemId] = setInterval(async () => {
      try {
        const resp = await fetch(`/api/manual-intel/${itemId}`)
        if (!resp.ok) return
        const updated = await resp.json()
        setItems(prev => prev.map(i => i.id === itemId ? updated : i))
        if (updated.quick_read !== '') {
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
    setSelectedIds(prev => { const next = new Set(prev); next.delete(itemId); return next })
  }

  async function handleReanalyze(itemId) {
    await fetch(`/api/manual-intel/${itemId}/reanalyze`, { method: 'POST' })
    setItems(prev => prev.map(i => i.id === itemId ? { ...i, quick_read: '' } : i))
    startPolling(itemId)
  }

  function handleUpdateItem(itemId, updates) {
    setItems(prev => prev.map(i => i.id === itemId ? { ...i, ...updates } : i))
  }

  function toggleSelect(itemId) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.has(itemId) ? next.delete(itemId) : next.add(itemId)
      return next
    })
  }

  async function handleGenerateSharePage() {
    setGenerating(true)
    try {
      const ids = [...selectedIds]
      const res = await fetch('/api/manual-intel/generate-share-page', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: ids }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      window.open(data.url, '_blank')
    } catch (e) {
      console.error('[generate share page] failed:', e)
    } finally {
      setGenerating(false)
    }
  }

  const filtered = platformFilter === 'all' ? items : items.filter(i => i.source_platform === platformFilter)
  const usedPlatforms = [...new Set(items.map(i => i.source_platform).filter(Boolean))]

  return (
    <div>
      {/* Page header */}
      <div style={{ padding: '16px 28px 12px', borderBottom: '1px solid var(--border)', background: 'var(--bg-primary)' }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
          📌 我的情报收藏
          <span style={{ fontSize: 12, background: 'var(--bg-secondary)', color: 'var(--text-muted)', borderRadius: 10, padding: '2px 8px' }}>
            {items.length}
          </span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>速读自动生成，商业与研发机会按需生成</p>
        <ShareBar
          count={selectedIds.size}
          onClear={() => setSelectedIds(new Set())}
          onGenerate={handleGenerateSharePage}
          generating={generating}
        />
      </div>

      {/* Input form */}
      <div style={{ margin: '16px 28px', background: 'var(--bg-primary)', borderRadius: 10, border: '1px solid var(--border)', padding: 16 }}>
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
              boxSizing: 'border-box',
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
      <div style={{ padding: '0 28px 28px', display: 'flex', flexDirection: 'column', gap: 10 }}>
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
              onUpdateItem={handleUpdateItem}
              selected={selectedIds.has(item.id)}
              onToggle={() => toggleSelect(item.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
