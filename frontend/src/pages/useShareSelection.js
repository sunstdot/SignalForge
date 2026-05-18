import { useState, useEffect, useCallback } from 'react'

export function useShareSelection(date) {
  const key = `sf-selection-${date}`

  const [selection, setSelection] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(key)) || { signal_ids: [], opportunity_ids: [] }
    } catch {
      return { signal_ids: [], opportunity_ids: [] }
    }
  })
  const [generating, setGenerating] = useState(false)

  // 当 date 变化时从 localStorage 重新加载
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(key))
      setSelection(stored || { signal_ids: [], opportunity_ids: [] })
    } catch {
      setSelection({ signal_ids: [], opportunity_ids: [] })
    }
  }, [key])

  // 选中状态变化时写入 localStorage
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(selection))
  }, [key, selection])

  const toggleSignal = useCallback((id) => {
    setSelection(s => ({
      ...s,
      signal_ids: s.signal_ids.includes(id)
        ? s.signal_ids.filter(x => x !== id)
        : [...s.signal_ids, id],
    }))
  }, [])

  const toggleOpportunity = useCallback((id) => {
    setSelection(s => ({
      ...s,
      opportunity_ids: s.opportunity_ids.includes(id)
        ? s.opportunity_ids.filter(x => x !== id)
        : [...s.opportunity_ids, id],
    }))
  }, [])

  const clearAll = useCallback(() => {
    setSelection({ signal_ids: [], opportunity_ids: [] })
  }, [])

  const generate = useCallback(async () => {
    setGenerating(true)
    try {
      const res = await fetch('/api/share-pages/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date,
          signal_ids: selection.signal_ids,
          opportunity_ids: selection.opportunity_ids,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      window.open(`/api/share-pages/${date}.html`, '_blank')
    } catch (e) {
      console.error('[generate share page] failed:', e)
    } finally {
      setGenerating(false)
    }
  }, [date, selection])

  return {
    signalIds: selection.signal_ids,
    opportunityIds: selection.opportunity_ids,
    count: selection.signal_ids.length + selection.opportunity_ids.length,
    toggleSignal,
    toggleOpportunity,
    clearAll,
    generating,
    generate,
  }
}

export function ShareSelectionBar({ signalIds, opportunityIds, generating, onClear, onGenerate }) {
  const count = signalIds.length + opportunityIds.length
  if (count === 0) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '6px 0', marginTop: 6, fontSize: 12,
    }}>
      <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
        已选{' '}
        <strong style={{ color: 'var(--text-primary)' }}>{signalIds.length} 条情报</strong>
        {' · '}
        <strong style={{ color: 'var(--text-primary)' }}>{opportunityIds.length} 个机会</strong>
      </span>
      <span style={{ flex: 1 }} />
      <button
        onClick={onClear}
        disabled={generating}
        style={{
          background: 'transparent',
          border: '1px solid var(--border)',
          color: 'var(--text-muted)',
          padding: '3px 10px',
          borderRadius: 5,
          fontSize: 11,
          cursor: 'pointer',
        }}
      >
        清空
      </button>
      <button
        onClick={onGenerate}
        disabled={generating || count === 0}
        style={{
          background: '#9a3412',
          border: 'none',
          color: 'white',
          padding: '3px 12px',
          borderRadius: 5,
          fontSize: 11,
          fontWeight: 600,
          cursor: generating ? 'default' : 'pointer',
          opacity: generating ? 0.6 : 1,
        }}
      >
        {generating ? '生成中...' : '生成分享页 →'}
      </button>
    </div>
  )
}
