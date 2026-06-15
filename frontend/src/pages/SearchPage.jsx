import { useState, useEffect, useRef, useCallback } from 'react'

const SOURCE_TYPE_LABELS = {
  arxiv: '论文',
  github: '仓库',
  model: '模型',
  news: '资讯',
  blog: 'AI公司博客',
  wechat: '微信公众号',
  reddit: 'Reddit',
  x: 'X',
  hn: 'Hacker News',
  youtube: 'YouTube',
  tiktok: 'TikTok',
  instagram: 'Instagram',
}

const SOURCE_TYPE_COLORS = {
  arxiv:  { bg: '#eef2ff', color: '#4338ca' },
  github: { bg: '#f0fdf4', color: '#166534' },
  model:  { bg: '#fdf4ff', color: '#7e22ce' },
  news:   { bg: '#fff7ed', color: '#c2410c' },
  blog:   { bg: '#f0f9ff', color: '#0369a1' },
  wechat: { bg: '#f0fdf4', color: '#15803d' },
  reddit:    { bg: '#fff7ed', color: '#c2410c' },
  x:         { bg: '#f1f5f9', color: '#0f172a' },
  hn:        { bg: '#fff7ed', color: '#ea580c' },
  youtube:   { bg: '#fef2f2', color: '#b91c1c' },
  tiktok:    { bg: '#f5f3ff', color: '#6d28d9' },
  instagram: { bg: '#fdf2f8', color: '#be185d' },
}

// 情报搜索只展示 last30days 的社交来源，平台筛选 chip 限定这 6 个
const L30_TYPES = ['reddit', 'x', 'hn', 'youtube', 'tiktok', 'instagram']

function SourceBadge({ type }) {
  const label = SOURCE_TYPE_LABELS[type] || type
  const style = SOURCE_TYPE_COLORS[type] || { bg: '#f3f4f6', color: '#6b7280' }
  return (
    <span style={{
      fontSize: 11, padding: '2px 7px', borderRadius: 4, fontWeight: 500,
      background: style.bg, color: style.color,
    }}>
      {label}
    </span>
  )
}

function HighlightText({ text, keyword }) {
  if (!keyword || !text) return <span>{text}</span>
  const parts = text.split(new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'))
  return (
    <span>
      {parts.map((part, i) =>
        part.toLowerCase() === keyword.toLowerCase()
          ? <mark key={i} style={{ background: '#fef9c3', color: '#854d0e', borderRadius: 2, padding: '0 1px' }}>{part}</mark>
          : part
      )}
    </span>
  )
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [sourceType, setSourceType] = useState('')
  const [results, setResults] = useState([])
  const [searched, setSearched] = useState(false)
  const [total, setTotal] = useState(0)
  const [researching, setResearching] = useState(false)
  const [researchTopic, setResearchTopic] = useState('')
  const [researchError, setResearchError] = useState('')
  const inputRef = useRef(null)
  // 递增 token：新搜索会让上一次轮询自动失效
  const searchTokenRef = useRef(0)
  // 记住已研究的话题，供平台 chip 切换时本地重过滤（不重复触发研究）
  const lastTopicRef = useRef('')

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // 拉取该话题已导入的 last30days 条目（仅 last30days 来源，可选按平台筛选）
  const fetchTopicResults = useCallback(async (topic, st) => {
    const params = new URLSearchParams({ limit: 500 })
    if (st) params.set('source_type', st)
    const res = await fetch(`/api/content?${params}`)
    const data = await res.json()
    const items = data.items || []
    const keyword = topic.trim().toLowerCase()
    return items.filter(item => {
      if (item.metadata?.origin !== 'last30days') return false
      if (!keyword) return true
      const text = [item.title, item.summary, item.tags?.join(' '), item.metadata?.topic]
        .filter(Boolean).join(' ').toLowerCase()
      return text.includes(keyword)
    })
  }, [])

  // 直接触发 wingsbot 跑 last30days，轮询完成后展示该话题结果
  const runResearch = useCallback(async (topic, st, token) => {
    setResearching(true)
    setResearchTopic(topic)
    setResearchError('')
    try {
      const start = await fetch('/api/last30days/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic }),
      }).then(r => r.json())
      const jobId = start.job_id
      // 轮询，最多约 10 分钟（200 × 3s）
      for (let i = 0; i < 200; i++) {
        await new Promise(r => setTimeout(r, 3000))
        if (searchTokenRef.current !== token) return // 已被新搜索取代
        const job = await fetch(`/api/last30days/research/${jobId}`).then(r => r.json())
        if (job.status === 'done') {
          const filtered = await fetchTopicResults(topic, st)
          if (searchTokenRef.current !== token) return
          setTotal(filtered.length)
          setResults(filtered.slice(0, 100))
          return
        }
        if (job.status === 'error') {
          setResearchError(job.error || '研究失败')
          return
        }
      }
      setResearchError('研究超时，请稍后重试')
    } catch (e) {
      setResearchError(String(e))
    } finally {
      if (searchTokenRef.current === token) setResearching(false)
    }
  }, [fetchTopicResults])

  // 情报搜索 = 直接对关键词跑 last30days（不查本地情报）
  const doSearch = useCallback(async (q, st) => {
    const topic = q.trim()
    if (!topic) return
    const token = ++searchTokenRef.current
    lastTopicRef.current = topic
    setSearched(true)
    setResearchError('')
    setResults([])
    setTotal(0)
    await runResearch(topic, st, token)
  }, [runResearch])

  const handleSubmit = (e) => {
    e.preventDefault()
    doSearch(query, sourceType)
  }

  // 平台 chip：对已研究的话题本地重过滤，不重复触发 last30days
  const handleTypeChange = async (type) => {
    const next = sourceType === type ? '' : type
    setSourceType(next)
    const topic = lastTopicRef.current
    if (topic && !researching) {
      const filtered = await fetchTopicResults(topic, next)
      setTotal(filtered.length)
      setResults(filtered.slice(0, 100))
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
          🔍 情报搜索
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
          输入话题，实时聚合 Reddit / X / Hacker News / YouTube / TikTok / Instagram 最近 30 天的讨论
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSubmit} style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="输入话题，实时研究全网最近 30 天..."
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 8, fontSize: 15,
              border: '1px solid var(--border)', background: 'var(--bg-primary)',
              color: 'var(--text-primary)', outline: 'none',
              boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
            }}
            onFocus={e => { e.target.style.borderColor = '#3b82f6' }}
            onBlur={e => { e.target.style.borderColor = 'var(--border)' }}
          />
          <button
            type="submit"
            style={{
              padding: '10px 22px', borderRadius: 8, background: '#2563eb',
              color: '#fff', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 600,
            }}
          >
            搜索
          </button>
        </div>
      </form>

      {/* Type filters */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>
        {L30_TYPES.map((type) => {
          const label = SOURCE_TYPE_LABELS[type] || type
          const active = sourceType === type
          const style = SOURCE_TYPE_COLORS[type] || {}
          return (
            <button
              key={type}
              onClick={() => handleTypeChange(type)}
              style={{
                padding: '5px 14px', borderRadius: 20, fontSize: 13, cursor: 'pointer',
                fontWeight: active ? 600 : 400,
                border: active ? `1.5px solid ${style.color || '#3b82f6'}` : '1px solid var(--border)',
                background: active ? (style.bg || '#eef2ff') : 'var(--bg-secondary)',
                color: active ? (style.color || '#3b82f6') : 'var(--text-secondary)',
                transition: 'all 0.15s',
              }}
            >
              {label}
            </button>
          )
        })}
        {(sourceType) && (
          <button
            onClick={() => handleTypeChange(sourceType)}
            style={{
              padding: '5px 12px', borderRadius: 20, fontSize: 13, cursor: 'pointer',
              border: '1px solid var(--border)', background: 'transparent',
              color: 'var(--text-muted)',
            }}
          >
            ✕ 清除筛选
          </button>
        )}
      </div>

      {/* Results */}
      {/* 正在实时研究 */}
      {researching && (
        <div style={{
          textAlign: 'center', padding: '56px 0',
          color: 'var(--text-muted)', fontSize: 15,
        }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🔭</div>
          <div>
            正在实时研究「<strong style={{ color: 'var(--text-primary)' }}>{researchTopic}</strong>」最近 30 天的讨论…
          </div>
          <div style={{ fontSize: 13, marginTop: 8 }}>
            会从 Reddit / X / Hacker News / YouTube / TikTok / Instagram 聚合，可能需要几分钟，请稍候
          </div>
        </div>
      )}

      {/* 研究失败 */}
      {!researching && researchError && (
        <div style={{
          textAlign: 'center', padding: '56px 0',
          color: 'var(--text-muted)', fontSize: 15,
        }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>⚠️</div>
          <div>实时研究失败</div>
          <div style={{ fontSize: 13, marginTop: 8, color: '#b91c1c', maxWidth: 520, margin: '8px auto 0' }}>
            {researchError}
          </div>
        </div>
      )}

      {!researching && !researchError && searched && (
        <div style={{ marginBottom: 12, fontSize: 13, color: 'var(--text-muted)' }}>
          共找到 <strong style={{ color: 'var(--text-primary)' }}>{total}</strong> 条情报
          {total > 100 && '，显示前 100 条'}
        </div>
      )}

      {!researching && !researchError && searched && results.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '64px 0',
          color: 'var(--text-muted)', fontSize: 15,
        }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🔎</div>
          <div>没有找到「{researchTopic}」的相关讨论</div>
          <div style={{ fontSize: 13, marginTop: 6 }}>换个话题试试？</div>
        </div>
      )}

      {!researching && results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {results.map((item, idx) => (
            <div
              key={item.id || idx}
              style={{
                padding: '16px 4px',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 6 }}>
                <SourceBadge type={item.source_type} />
                {item.date && (
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 1 }}>{item.date}</span>
                )}
              </div>
              <div style={{ marginBottom: 6 }}>
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: 15, fontWeight: 600, color: '#2563eb',
                      textDecoration: 'none', lineHeight: 1.4,
                    }}
                    onMouseEnter={e => e.target.style.textDecoration = 'underline'}
                    onMouseLeave={e => e.target.style.textDecoration = 'none'}
                  >
                    <HighlightText text={item.title} keyword={query.trim()} />
                  </a>
                ) : (
                  <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                    <HighlightText text={item.title} keyword={query.trim()} />
                  </span>
                )}
              </div>
              {item.summary && (
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
                  <HighlightText text={item.summary.slice(0, 200) + (item.summary.length > 200 ? '…' : '')} keyword={query.trim()} />
                </p>
              )}
              {item.tags?.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                  {item.tags.slice(0, 6).map(tag => (
                    <span
                      key={tag}
                      onClick={() => { setQuery(tag); doSearch(tag, sourceType) }}
                      style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 4,
                        background: 'var(--bg-secondary)', color: 'var(--text-muted)',
                        cursor: 'pointer', border: '1px solid var(--border)',
                      }}
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!searched && (
        <div style={{
          textAlign: 'center', padding: '64px 0',
          color: 'var(--text-muted)', fontSize: 14,
        }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📡</div>
          <div>输入话题，实时研究全网最近 30 天的讨论</div>
        </div>
      )}
    </div>
  )
}
