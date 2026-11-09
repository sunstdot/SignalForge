import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import './ResearchPage.css'
import { parseBlocks, parseInline, shortCite } from './researchMarkdown'

const STAGE_LABELS = {
  created: '已创建',
  plan: '拆解问题',
  search: '检索来源',
  fetch: '抓取正文',
  extract: '抽取证据',
  verify: '核验事实',
  synthesize: '撰写成稿',
  validate: '校验引用',
  done: '完成',
}

const VERDICT_LABELS = {
  confirmed: '已证实',
  single: '单源待核',
  conflict: '存在冲突',
}

const FETCH_LABELS = {
  ok: '已抓取',
  paywalled: '付费墙',
  blocked: '被拦截',
  unreachable: '不可达',
  error: '抓取失败',
  skipped: '未抓取',
}

function formatTime(value) {
  if (!value) return ''
  return value.replace('T', ' ').slice(0, 16)
}

// 引用角标：连续引用收成一个上标组，最多展示 3 个，其余折叠为 +N。
// 早先把每个 id 都渲染成带边框的按钮，一段里出现十几次，把正文切成碎片。
function CitationMark({ ids, onCitationClick }) {
  const shown = ids.slice(0, 3)
  const rest = ids.length - shown.length
  return (
    <span className="research-cite-group">
      {shown.map((id, index) => (
        <button
          key={id}
          type="button"
          className="research-cite"
          onClick={() => onCitationClick(id)}
          title={`查看证据 ${id}`}
        >
          {index === 0 ? '' : ','}
          {shortCite(id)}
        </button>
      ))}
      {rest > 0 && <span className="research-cite-more">+{rest}</span>}
    </span>
  )
}

function renderInline(text, onCitationClick, keyPrefix) {
  return parseInline(text).map((token, index) => {
    const key = `${keyPrefix}-${index}`
    if (token.type === 'bold') return <strong key={key}>{token.value}</strong>
    if (token.type === 'code') return <code key={key} className="research-code">{token.value}</code>
    if (token.type === 'link') {
      return <a key={key} href={token.href} target="_blank" rel="noreferrer">{token.label}</a>
    }
    if (token.type === 'cite') {
      return <CitationMark key={key} ids={token.ids} onCitationClick={onCitationClick} />
    }
    return <span key={key}>{token.value}</span>
  })
}

function renderBlocks(markdown, onCitationClick) {
  return parseBlocks(markdown).map((block, index) => {
    const key = `b-${index}`
    if (block.type === 'heading') {
      const Tag = `h${Math.min(block.level + 1, 4)}`
      return <Tag key={key} className="research-h">{block.text}</Tag>
    }
    if (block.type === 'quote') {
      return (
        <blockquote key={key} className="research-quote">
          {renderInline(block.text, onCitationClick, key)}
        </blockquote>
      )
    }
    if (block.type === 'list') {
      const Tag = block.ordered ? 'ol' : 'ul'
      return (
        <Tag key={key} className="research-list">
          {block.items.map((item, i) => (
            <li key={`${key}-${i}`}>{renderInline(item, onCitationClick, `${key}-${i}`)}</li>
          ))}
        </Tag>
      )
    }
    return (
      <p key={key} className="research-p">
        {renderInline(block.text, onCitationClick, key)}
      </p>
    )
  })
}

function RunComposer({ onCreated }) {
  const [topic, setTopic] = useState('')
  const [questions, setQuestions] = useState('')
  const [asOf, setAsOf] = useState(() => new Date().toISOString().slice(0, 10))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!topic.trim()) {
      setError('请填写调研主题')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const resp = await fetch('/api/research/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          questions: questions.split('\n').map(q => q.trim()).filter(Boolean),
          as_of: asOf,
        }),
      })
      if (!resp.ok) throw new Error(`创建失败（${resp.status}）`)
      const data = await resp.json()
      setTopic('')
      setQuestions('')
      onCreated(data.run)
    } catch (err) {
      setError(err.message || '创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="research-composer">
      <label className="research-label">调研主题</label>
      <input
        className="research-input"
        value={topic}
        onChange={e => setTopic(e.target.value)}
        placeholder="例：Anthropic 的组织结构与管理体系"
      />

      <label className="research-label">想回答的问题（每行一个，可留空由系统拆解）</label>
      <textarea
        className="research-textarea"
        value={questions}
        onChange={e => setQuestions(e.target.value)}
        rows={4}
        placeholder={'有几个大的职能模块，主要负责人是谁？\n管理者背景与管理要求？\n人才如何选拔、考核与保留？'}
      />

      <div className="research-row">
        <div>
          <label className="research-label">事实截止日期</label>
          <input
            className="research-input research-input--date"
            type="date"
            value={asOf}
            onChange={e => setAsOf(e.target.value)}
          />
        </div>
        <button type="button" className="research-submit" onClick={submit} disabled={submitting}>
          {submitting ? '创建中…' : '开始调研'}
        </button>
      </div>
      {error && <div className="research-error">{error}</div>}
      <p className="research-hint">
        一次调研通常需要 20-40 分钟。系统会先拆解问题，再检索、抓取、抽取带原文出处的证据，
        最后校验每一处引用。可以离开页面，稍后回来查看进度。
      </p>
    </div>
  )
}

function CitationDrawer({ claim, onClose }) {
  if (!claim) return null
  return (
    <aside className="research-drawer">
      <div className="research-drawer-head">
        <span className="research-badge">{VERDICT_LABELS[claim.verdict] || claim.verdict}</span>
        <button type="button" className="research-drawer-close" onClick={onClose}>关闭</button>
      </div>
      <div className="research-drawer-claim">{claim.text}</div>
      <div className="research-label">原文出处</div>
      <blockquote className="research-drawer-quote">{claim.quote}</blockquote>
      <a className="research-drawer-link" href={claim.source_url} target="_blank" rel="noreferrer">
        {claim.source_title || claim.source_url}
      </a>
      {claim.as_of && <div className="research-drawer-meta">事实时点：{claim.as_of}</div>}
    </aside>
  )
}

function ResearchPage() {
  const { runId } = useParams()
  const navigate = useNavigate()
  const [runs, setRuns] = useState([])
  const [run, setRun] = useState(null)
  const [report, setReport] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [sources, setSources] = useState([])
  const [claims, setClaims] = useState([])
  const [activeClaim, setActiveClaim] = useState(null)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadRuns = useCallback(async () => {
    const resp = await fetch('/api/research/runs')
    if (!resp.ok) return
    const data = await resp.json()
    setRuns(data.runs || [])
  }, [])

  const loadDetail = useCallback(async id => {
    if (!id) return
    setLoading(true)
    try {
      const runResp = await fetch(`/api/research/runs/${id}`)
      if (runResp.ok) {
        const data = await runResp.json()
        setRun(data.run)
      }
      const sourcesResp = await fetch(`/api/research/runs/${id}/sources`)
      const sourceRows = sourcesResp.ok ? (await sourcesResp.json()).sources || [] : []
      setSources(sourceRows)
      const sourceMap = new Map(sourceRows.map(s => [s.id, s]))

      const claimsResp = await fetch(`/api/research/runs/${id}/claims`)
      const rows = claimsResp.ok ? (await claimsResp.json()).claims || [] : []
      setClaims(rows.map(row => ({
        ...row,
        source_url: sourceMap.get(row.source_id)?.url || '',
        source_title: sourceMap.get(row.source_id)?.title || '',
      })))

      const reportResp = await fetch(`/api/research/runs/${id}/report`)
      if (reportResp.ok) {
        const data = await reportResp.json()
        setReport(data.report)
        setMetrics(data.metrics)
      } else {
        setReport(null)
        setMetrics(null)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRuns()
    fetch('/api/research/status').then(r => r.ok ? r.json() : null).then(setStatus).catch(() => {})
  }, [loadRuns])

  useEffect(() => {
    loadDetail(runId)
  }, [runId, loadDetail])

  // 运行中每 15 秒刷新一次，跑完就停
  useEffect(() => {
    if (!runId || !run || ['done', 'failed', 'validated'].includes(run.status) || ['done', 'validate'].includes(run.stage)) {
      return undefined
    }
    const timer = setInterval(() => {
      loadDetail(runId)
      loadRuns()
    }, 15000)
    return () => clearInterval(timer)
  }, [runId, run, loadDetail, loadRuns])

  const claimMap = useMemo(() => new Map(claims.map(c => [c.id, c])), [claims])

  const counts = useMemo(() => {
    const base = { confirmed: 0, single: 0, conflict: 0 }
    for (const claim of claims) base[claim.verdict] = (base[claim.verdict] || 0) + 1
    return base
  }, [claims])

  const fetchProblems = useMemo(
    () => sources.filter(s => s.fetch_status && s.fetch_status !== 'ok'),
    [sources],
  )

  return (
    <div className="research-page">
      <header className="research-header">
        <div>
          <h1 className="research-title">深度调研</h1>
          <p className="research-sub">结构化拆解 → 多源检索 → 证据抽取 → 引用校验。每条结论都能回到原文。</p>
        </div>
        {status?.degraded && (
          <div className="research-warn">
            当前搜索后端为 {status.backend}（降级模式），检索覆盖不完整。配置 TAVILY_API_KEY 可启用通用网络搜索。
          </div>
        )}
      </header>

      <div className="research-layout">
        <nav className="research-sidebar">
          <button
            type="button"
            className={`research-run-item ${!runId ? 'active' : ''}`}
            onClick={() => navigate('/research')}
          >
            + 新建调研
          </button>
          {runs.map(item => (
            <Link
              key={item.id}
              to={`/research/${item.id}`}
              className={`research-run-item ${item.id === runId ? 'active' : ''}`}
            >
              <span className="research-run-topic">{item.topic}</span>
              <span className="research-run-meta">
                {STAGE_LABELS[item.stage] || item.stage} · {formatTime(item.created_at)}
              </span>
            </Link>
          ))}
        </nav>

        <main className="research-main">
          {!runId && <RunComposer onCreated={created => { loadRuns(); navigate(`/research/${created.id}`) }} />}

          {runId && loading && !run && <div className="research-empty">加载中…</div>}

          {runId && run && (
            <>
              <div className="research-run-head">
                <h2 className="research-run-title">{run.topic}</h2>
                <span className={`research-stage research-stage--${run.status}`}>
                  {STAGE_LABELS[run.stage] || run.stage}
                </span>
              </div>
              <div className="research-stats">
                <div className="research-stat"><b>{metrics?.sources_total ?? sources.length}</b><span>来源</span></div>
                <div className="research-stat"><b>{metrics?.claims_total ?? claims.length}</b><span>论断</span></div>
                <div className="research-stat"><b>{counts.confirmed}</b><span>已证实</span></div>
                <div className="research-stat"><b>{counts.single}</b><span>单源待核</span></div>
                <div className="research-stat"><b>{counts.conflict}</b><span>冲突</span></div>
                <div className="research-stat"><b>{fetchProblems.length}</b><span>抓取受阻</span></div>
              </div>

              {run.status === 'failed' && (
                <div className="research-error">运行失败：{run.error || '未知错误'}</div>
              )}

              {report ? (
                <article className="research-report">
                  {renderBlocks(report.markdown, id => setActiveClaim(claimMap.get(id) || null))}
                </article>
              ) : (
                <div className="research-empty">
                  {run.status === 'failed' ? '没有生成成稿。' : '报告生成中，完成后会自动出现在这里。'}
                </div>
              )}

              {fetchProblems.length > 0 && (
                <section className="research-section">
                  <h3 className="research-section-title">抓取受阻的来源（{fetchProblems.length}）</h3>
                  <p className="research-hint">
                    这些来源没能取到正文，相应内容未参与核验。缺口是显式的，不是没找到。
                  </p>
                  <ul className="research-source-list">
                    {fetchProblems.map(source => (
                      <li key={source.id} className="research-source-item">
                        <span className={`research-tier research-tier--${source.tier}`}>{source.tier}</span>
                        <a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a>
                        <span className="research-source-status">
                          {FETCH_LABELS[source.fetch_status] || source.fetch_status}
                          {source.fetch_detail ? `：${source.fetch_detail}` : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {sources.length > 0 && (
                <section className="research-section">
                  <h3 className="research-section-title">全部来源（{sources.length}）</h3>
                  <ul className="research-source-list">
                    {sources.map(source => (
                      <li key={source.id} className="research-source-item">
                        <span className={`research-tier research-tier--${source.tier}`}>{source.tier}</span>
                        <a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a>
                        <span className="research-source-status">{FETCH_LABELS[source.fetch_status] || source.fetch_status}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}
        </main>

        <CitationDrawer claim={activeClaim} onClose={() => setActiveClaim(null)} />
      </div>
    </div>
  )
}

export default ResearchPage
