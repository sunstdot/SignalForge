import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  buildDailyOpportunityPost,
  getTopOpportunities,
  normalizeBusinessOpportunity,
  normalizeRdevOpportunity,
} from './dailyContent'
import { loadDailyOpportunityData } from './dailyOpportunityData'

function DailyOpportunityPage() {
  const { date } = useParams()
  const [business, setBusiness] = useState([])
  const [rdev, setRdev] = useState(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let active = true

    async function load() {
      setLoading(true)
      try {
        const data = await loadDailyOpportunityData(date)
        if (!active) return
        setBusiness(data.business)
        setRdev(data.rdev)
      } catch (error) {
        if (active) console.error('Failed to load daily opportunities:', error)
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => { active = false }
  }, [date])

  const businessTop = useMemo(() => business.map(normalizeBusinessOpportunity).slice(0, 3), [business])
  const rdevTop = useMemo(() => (rdev?.solutions || []).map(normalizeRdevOpportunity).slice(0, 3), [rdev])
  const allTop = useMemo(() => getTopOpportunities(business, rdev || {}, 3), [business, rdev])
  const post = useMemo(() => buildDailyOpportunityPost({ date, business, rdev: rdev || {} }), [business, date, rdev])

  async function copyPost() {
    await navigator.clipboard.writeText(`${post.title}\n\n${post.body}\n\n${post.tags}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
          <span className="loading-pulse">▌</span>
          <span className="text-sm">加载今日机会中...</span>
        </div>
      </div>
    )
  }

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
            <span style={{ color: 'var(--accent-blue)' }}>今日 AI 情报机会</span>
          </div>
        </div>
      </header>

      <main className="daily-opportunity-page">
        <section className="daily-publisher daily-publisher-opportunity">
          <div className="daily-publisher-main">
            <div>
              <span className="daily-eyebrow">今日 AI 情报机会</span>
              <h1>今天从情报里能做什么</h1>
              <p>把商业机会和研发机会合并成一篇固定栏目，适合每天直接发布。</p>
            </div>
            <div className="daily-actions">
              <Link to={`/opportunities/${date}`} className="daily-action-link">查看完整机会看板</Link>
              <button onClick={copyPost} className="daily-copy-btn">
                {copied ? '已复制' : '复制小红书文案'}
              </button>
            </div>
          </div>

          <div className="daily-publisher-grid">
            <div className="xhs-shot-card xhs-shot-card-opportunity">
              <span>{date}</span>
              <h2>今日 AI 情报机会</h2>
              {allTop.map((item, index) => (
                <div key={`${item.kind}-${item.title}`} className="xhs-shot-row">
                  <b>{index + 1}</b>
                  <p>{item.title}</p>
                </div>
              ))}
            </div>
            <div className="daily-copy-preview">
              <strong>{post.title}</strong>
              <pre>{post.body}</pre>
              <small>{post.tags}</small>
            </div>
          </div>
        </section>

        <section className="daily-columns">
          <OpportunityColumn title="商业机会" items={businessTop} empty="暂无商业机会缓存，可以先在今日 AI 情报页生成机会。" />
          <OpportunityColumn title="研发机会" items={rdevTop} empty="暂无研发机会缓存，可以先生成研发效能分析。" />
        </section>
      </main>
    </>
  )
}

function OpportunityColumn({ title, items, empty }) {
  return (
    <section className="daily-column">
      <div className="daily-column-head">
        <h2>{title}</h2>
        <span>{items.length} 个</span>
      </div>
      {items.length === 0 ? (
        <p className="daily-empty">{empty}</p>
      ) : (
        <div className="daily-card-list">
          {items.map((item, index) => (
            <article key={`${item.kind}-${item.title}`} className="daily-opportunity-card">
              <div className="daily-card-top">
                <b>#{index + 1}</b>
                <span>{item.score}/{item.scoreMax}</span>
              </div>
              <h3>{item.title}</h3>
              {item.sourceTitle && <p className="daily-source">来源：{item.sourceTitle}</p>}
              {item.insight && <Detail label="趋势判断" value={item.insight} />}
              {item.form && <Detail label="可以怎么做" value={item.form} />}
              {item.action && <Detail label="下一步" value={item.action} />}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function Detail({ label, value }) {
  return (
    <div className="daily-detail">
      <span>{label}</span>
      <p>{value}</p>
    </div>
  )
}

export default DailyOpportunityPage
