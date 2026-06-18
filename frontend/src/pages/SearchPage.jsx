import { useState, useRef, useCallback, useEffect } from 'react'

/* ------------------------------------------------------------------ *
 * 情报搜索 · 输入 topic → 实时跑 last30days → 渲染综合简报 + 情报时间线
 * 数据来自 POST /api/search/brief（异步 job + 轮询）。
 * ------------------------------------------------------------------ */

const PLATFORM = {
  x:         { c: '#15171a', label: 'X',         ava: 'X'  },
  reddit:    { c: '#ff4500', label: 'Reddit',    ava: 'r/' },
  hn:        { c: '#ff6600', label: 'HN',        ava: 'HN' },
  youtube:   { c: '#ff0000', label: 'YouTube',   ava: 'YT' },
  tiktok:    { c: '#111111', label: 'TikTok',    ava: 'TT' },
  instagram: { c: '#c13584', label: 'Instagram', ava: 'IG' },
}
const PF = (p) => PLATFORM[p] || { c: '#888', label: p || '?', ava: (p || '?').slice(0, 2).toUpperCase() }
const TEAL = '#0f7a52'
const GOLD = '#a66a00'

function richHtml(s) {
  if (!s) return ''
  return s
    .replace(/\{b\}/g, '<b>').replace(/\{\/b\}/g, '</b>')
    .replace(/<src>/g, '<span class="sf-src">').replace(/<\/src>/g, '</span>')
    .replace(/<q>/g, '<span class="sf-q">').replace(/<\/q>/g, '</span>')
    .replace(/<hl>/g, '<span class="sf-hl">').replace(/<\/hl>/g, '</span>')
    .replace(/<num>/g, '<span class="sf-num">').replace(/<\/num>/g, '</span>')
    .replace(/<c>/g, '<span class="sf-mono">').replace(/<\/c>/g, '</span>')
}
const RH = (s) => <span dangerouslySetInnerHTML={{ __html: richHtml(s) }} />

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

// 静态部署模式：用 VITE_STATIC_DATA=1 构建时，前端直接读 data/search_cache 下的缓存文件，
// 不请求后端接口（这样可以只部署前端就看到已缓存的情报）。
const STATIC = import.meta.env.VITE_STATIC_DATA === '1'
const slugify = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'topic'
const briefUrl = (topic, slug) =>
  STATIC
    ? `/data/search_cache/briefs/${slug || slugify(topic)}.json`
    : `/api/search/brief?topic=${encodeURIComponent(topic)}`

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [brief, setBrief] = useState(null)
  const [status, setStatus] = useState('idle')   // idle | running | done | error
  const [error, setError] = useState('')
  const [topic, setTopic] = useState('')
  const [plat, setPlat] = useState('all')
  const [featOnly, setFeatOnly] = useState(false)
  const [open, setOpen] = useState({})
  const [answered, setAnswered] = useState({})
  const [history, setHistory] = useState([])
  const inputRef = useRef(null)
  const tokenRef = useRef(0)

  const loadHistory = useCallback(async () => {
    try {
      if (STATIC) {
        const r = await fetch('/data/search_cache/history.json')
        setHistory(r.ok ? await r.json() : [])
      } else {
        const r = await fetch('/api/search/history')
        if (r.ok) setHistory((await r.json()).history || [])
      }
    } catch { /* ignore */ }
  }, [])

  // 读取某话题已缓存的 brief（静态模式读 data 文件，否则走后端）
  const fetchCachedBrief = useCallback(async (topic, slug) => {
    const r = await fetch(briefUrl(topic, slug))
    return r.ok ? await r.json() : null
  }, [])

  // 轮询某个 job 直到 done/error；done 时把 brief 存入 sessionStorage 以便刷新后恢复
  const pollJob = useCallback(async (jid, token, t) => {
    try {
      for (let i = 0; i < 400; i++) {        // 先查再睡，最多约 20 分钟
        if (tokenRef.current !== token) return
        const job = await fetch(`/api/search/brief/${jid}`).then(r => r.json())
        if (job.status === 'done') {
          if (tokenRef.current !== token) return
          setBrief(job.brief); setStatus('done')
          // 只在浏览器留一个 topic 字符串；brief 实体在服务端 data/last30days 文件里
          try {
            sessionStorage.setItem('sf_topic', t)
            sessionStorage.removeItem('sf_job')
          } catch { /* ignore quota */ }
          loadHistory()
          return
        }
        if (job.status === 'error') {
          setError(job.error || '生成失败'); setStatus('error')
          try { sessionStorage.removeItem('sf_job') } catch { /* ignore */ }
          return
        }
        await sleep(3000)
      }
      setError('生成超时，请稍后重试'); setStatus('error')
    } catch (e) {
      setError(String(e)); setStatus('error')
    }
  }, [loadHistory])

  // 点搜索记录：直接读缓存，不重新抓取
  const openCached = useCallback(async (entry) => {
    const t = entry.topic
    const token = ++tokenRef.current
    setQuery(t); setTopic(t); setError(''); setBrief(null); setStatus('running')
    setPlat('all'); setFeatOnly(false); setOpen({}); setAnswered({})
    try {
      const b = await fetchCachedBrief(t, entry.slug)
      if (tokenRef.current !== token) return
      if (b) {
        setBrief(b); setStatus('done')
        try { sessionStorage.setItem('sf_topic', t); sessionStorage.removeItem('sf_job') } catch { /* ignore */ }
      } else {
        setError('该记录的缓存已不存在，请重新搜索'); setStatus('error')
      }
    } catch (e) { setError(String(e)); setStatus('error') }
  }, [fetchCachedBrief])

  // 回到首页（显示搜索记录）
  const goHome = useCallback(() => {
    ++tokenRef.current
    setStatus('idle'); setBrief(null); setError('')
    try { sessionStorage.removeItem('sf_topic'); sessionStorage.removeItem('sf_job') } catch { /* ignore */ }
    loadHistory()
  }, [loadHistory])

  const doSearch = useCallback(async () => {
    const t = query.trim()
    if (!t) return
    const token = ++tokenRef.current
    setStatus('running'); setError(''); setBrief(null); setTopic(t)
    setPlat('all'); setFeatOnly(false); setOpen({}); setAnswered({})
    try { sessionStorage.removeItem('sf_topic') } catch { /* ignore */ }
    // 静态部署模式：不发起实时研究，只尝试读该话题的缓存
    if (STATIC) {
      try {
        const b = await fetchCachedBrief(t)
        if (tokenRef.current !== token) return
        if (b) {
          setBrief(b); setStatus('done')
          try { sessionStorage.setItem('sf_topic', t) } catch { /* ignore */ }
        } else {
          setError('静态部署模式：没有该话题的缓存，请从下方搜索记录选择'); setStatus('error')
        }
      } catch (e) { setError(String(e)); setStatus('error') }
      return
    }
    let start
    try {
      start = await fetch('/api/search/brief', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: t }),
      }).then(r => r.json())
    } catch (e) { setError(String(e)); setStatus('error'); return }
    try { sessionStorage.setItem('sf_job', JSON.stringify({ jid: start.job_id, topic: t })) } catch { /* ignore */ }
    pollJob(start.job_id, token, t)
  }, [query, pollJob, fetchCachedBrief])

  // 刷新/重新挂载后恢复：未完成的 job 续上轮询；否则从服务端文件取回上次话题的 brief
  useEffect(() => {
    loadHistory()
    ;(async () => {
      try {
        const savedJob = sessionStorage.getItem('sf_job')
        if (!STATIC && savedJob) {           // 静态模式没有进行中的 job
          const { jid, topic: t } = JSON.parse(savedJob)
          const token = ++tokenRef.current
          setTopic(t); setQuery(t); setStatus('running')
          pollJob(jid, token, t)
          return
        }
        const t = sessionStorage.getItem('sf_topic')
        if (t) {
          const token = ++tokenRef.current
          const b = await fetchCachedBrief(t)
          if (tokenRef.current !== token) return
          if (b) { setBrief(b); setTopic(t); setQuery(t); setStatus('done') }
        }
      } catch { /* ignore */ }
    })()
  }, [pollJob, loadHistory, fetchCachedBrief])

  const toggleDeep = useCallback((k) => {
    setOpen(o => ({ ...o, [k]: !o[k] }))
    if (!answered[k]) setTimeout(() => setAnswered(a => ({ ...a, [k]: true })), 720)
  }, [answered])

  return (
    <div className="sf-search">
      <style>{STYLES}</style>

      <header className="sf-appbar">
        <div className="sf-ab-brand" onClick={goHome} style={{ cursor: 'pointer' }} title="返回搜索记录">
          <span className="m">🔍</span>情报搜索
        </div>
        <form className="sf-ab-search" onSubmit={(e) => { e.preventDefault(); doSearch() }}>
          <span className="si">🔍</span>
          <input ref={inputRef} value={query} onChange={(e) => setQuery(e.target.value)}
                 aria-label="搜索情报" placeholder="输入话题，实时研究全网最近 30 天…" autoFocus />
          {query && <span className="clear" title="清除" onClick={() => setQuery('')}>✕</span>}
        </form>
        <button className="sf-ab-btn" type="button" onClick={doSearch} disabled={status === 'running'}>
          {status === 'running' ? '研究中…' : '搜索'}
        </button>
      </header>

      <div className="sf-content">
        {status === 'idle' && (
          <div className="sf-home">
            <div className="sf-empty">
              <div className="ic">📡</div>
              <div className="t1">输入一个话题，开始实时情报研究</div>
              <div className="t2">从 Reddit / X / Hacker News / YouTube / TikTok / Instagram 聚合最近 30 天的讨论，合成综合简报与情报时间线</div>
            </div>
            {history.length > 0 && (
              <div className="sf-history">
                <div className="hh"><h3>搜索记录</h3><span className="meta">{history.length} 条 · 点击查看缓存</span></div>
                <div className="hlist">
                  {history.map(h => (
                    <button className="hrow" key={h.slug} onClick={() => openCached(h)}>
                      <span className="ht">{h.topic}</span>
                      <span className="hn">{h.total} 信源</span>
                      <span className="hd">{(h.updated_at || '').slice(0, 10)}</span>
                      <span className="hgo">→</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {status === 'running' && (
          <div className="sf-empty">
            <div className="ic">🔭</div>
            <div className="t1">正在实时研究「{topic}」最近 30 天的讨论…</div>
            <div className="t2">跨平台抓取 + 综合简报合成，可能需要几分钟，请稍候</div>
            <div className="sf-load"><span /><span /><span /></div>
          </div>
        )}

        {status === 'error' && (
          <div className="sf-empty">
            <div className="ic">⚠️</div>
            <div className="t1">研究失败</div>
            <div className="t2 err">{error}</div>
          </div>
        )}

        {status === 'done' && brief && <Brief brief={brief} plat={plat} setPlat={setPlat}
          featOnly={featOnly} setFeatOnly={setFeatOnly} open={open} answered={answered} toggleDeep={toggleDeep} />}
      </div>
    </div>
  )
}

function Brief({ brief, plat, setPlat, featOnly, setFeatOnly, open, answered, toggleDeep }) {
  const m = brief.meta
  const flatItems = brief.timeline.flatMap(g => g.items)
  const presentPlats = Object.entries(m.platforms || {}).filter(([, n]) => n > 0)
  const matchItem = (it) => (plat === 'all' || it.p === plat) && (!featOnly || it.feat)
  const shownCount = flatItems.filter(matchItem).length
  const has = (a) => Array.isArray(a) && a.length > 0

  return (
    <>
      {/* Result bar */}
      <div className="sf-resultbar">
        <span className="q">{brief.query}{brief.topic && brief.topic !== brief.query && <em>{brief.topic}</em>}</span>
        <span className="dot" />
        <span>综合 <b>{m.total}</b> 个信源</span>
        {presentPlats.map(([p, n]) => <span className="pill" key={p}>{PF(p).label} {n}</span>)}
        <span className="dot" />
        <span>{m.window}</span>
      </div>

      <div className="sf-layout">
        {/* MAIN */}
        <div className="sf-main">
          {/* HERO */}
          <section className="sf-sec sf-hero">
            {brief.kicker && <div className="sf-kicker"><span className="pulse" />{brief.kicker}</div>}
            <h1>{renderHeadline(brief.headline)}</h1>
            {brief.lede && <p className="sf-lede">{RH(brief.lede)}</p>}
            {brief.consensus && (brief.consensus.leftLabel || brief.consensus.rightLabel) && (
              <div className="sf-vbar-wrap">
                <div className="sf-vbar-ends">
                  <div className="e"><span className="lab">{brief.consensus.leftLabel}</span><span className="meta">{brief.consensus.leftSub}</span></div>
                  <div className="e r"><span className="lab">{brief.consensus.rightLabel}</span><span className="meta">{brief.consensus.rightSub}</span></div>
                </div>
                <div className="sf-vbar">
                  <span className="l" style={{ width: `${brief.consensus.left}%` }} />
                  <span className="r" style={{ width: `${brief.consensus.right}%` }} />
                  <span className="mid" />
                </div>
                <div className="sf-vbar-cap">社区共识 <b>{brief.consensus.left} / {brief.consensus.right}</b></div>
              </div>
            )}
          </section>

          {/* SYNTHESIS */}
          {has(brief.themes) && (
            <section className="sf-sec">
              <SecHead n="01" title="综合简报" k="Synthesis" />
              <div className="sf-themes">
                {brief.themes.map(t => (
                  <div className="sf-theme" key={t.n}>
                    <div className="tnum">{t.n}</div>
                    <div><h3>{t.title}</h3><p>{RH(t.html)}</p></div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* KEY PATTERNS */}
          {has(brief.patterns) && (
            <section className="sf-sec">
              <SecHead n="02" title="关键模式" k="Key Patterns" />
              <div className="sf-patterns">
                {brief.patterns.map(p => (
                  <div className={`sf-pcard${p.lead ? ' lead' : ''}`} style={p.wide ? { gridColumn: '1 / -1' } : null} key={p.n}>
                    {p.lead && <span className="badge">主线</span>}
                    <div className="pn">{p.n}</div>
                    <p>{p.text}</p>
                    {p.src && <span className="psrc">per <span className="tag">{p.src}</span></span>}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* DEEP DIVE */}
          {has(brief.deepDive) && (
            <section className="sf-sec">
              <SecHead n="03" title="让我深入" k="Follow-up" />
              <div className="sf-deep">
                <div className="sf-deep-sub">我现在是 {brief.query} 这个话题的专家了 —— 点开任一方向继续追问。</div>
                {brief.deepDive.map(d => (
                  <div className={`sf-ditem${open[d.k] ? ' open' : ''}`} key={d.k}>
                    <div className="dq" onClick={() => toggleDeep(d.k)}>
                      <span className="da">{d.k}</span>{d.q}<span className="dchev">▸</span>
                    </div>
                    <div className="danswer" style={{ maxHeight: open[d.k] ? 480 : 0 }}>
                      <div className="danswer-inner">
                        {!answered[d.k]
                          ? <span className="typing"><span className="dot" /><span className="dot" /><span className="dot" /> 正在深入分析…</span>
                          : <span dangerouslySetInnerHTML={{ __html: richHtml(d.a) }} />}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* TIMELINE */}
          <section className="sf-sec">
            <SecHead n="04" title="情报时间线" k="Timeline" />
            <div className="sf-tl-controls">
              <button className={`sf-tlchip${plat === 'all' ? ' on' : ''}`} onClick={() => setPlat('all')}>全部 {m.total}</button>
              {presentPlats.map(([p, n]) => (
                <button key={p} className={`sf-tlchip${plat === p ? ' on' : ''}`} onClick={() => setPlat(p)}>
                  <span className="c" style={{ background: PF(p).c }} />{PF(p).label} {n}
                </button>
              ))}
              <button className={`sf-tlchip feat${featOnly ? ' on' : ''}`} onClick={() => setFeatOnly(f => !f)}>✦ 仅看精选</button>
              <span className="sf-tl-count">显示 {shownCount} / {featOnly ? '精选' : m.total}</span>
            </div>

            <div className="sf-timeline">
              {brief.timeline.map(group => {
                const visible = group.items.filter(matchItem)
                if (!visible.length) return null
                return (
                  <div className="sf-tl-group" key={group.day}>
                    <div className="sf-tl-day"><span className="d">{group.day}</span><span className="dn">{group.dayNote}</span><span className="dln" /></div>
                    {visible.map((it, i) => (
                      <div className={`sf-tl-item${it.feat ? ' feat' : ''}`} key={i}>
                        <div className="sf-tl-side"><div className="t">{it.time || '—'}</div><div className="ago">{it.ago}</div></div>
                        <div className="sf-tl-dot" />
                        <div className="sf-tl-card">
                          <div className="top">
                            <span className="ava" style={{ background: PF(it.p).c }}>{PF(it.p).ava}</span>
                            <span className="who">{it.who}</span>
                            <span className="handle">{it.handle}</span>
                            <span className="right">
                              {it.feat && <span className="feat-badge">✦ 精选</span>}
                              <span className="score"><span className="sl">热度</span>{it.score}</span>
                            </span>
                          </div>
                          {it.url
                            ? <a className="ttl" href={it.url} target="_blank" rel="noopener noreferrer">{it.title}</a>
                            : <div className="ttl">{it.title}</div>}
                          <div className="sum">{it.sum}</div>
                          <div className="tags">
                            {(it.tags || []).map(tg => <span className="tag" key={tg}>{tg}</span>)}
                            {it.stat && <span className="stat">{it.stat}</span>}
                          </div>
                          {it.reason && <div className="reason"><span className="rl">推荐理由</span><p>{it.reason}</p></div>}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>

            {brief.rawNote && <div className="sf-tl-end"><span className="raw">📎 {brief.rawNote}</span></div>}
          </section>
        </div>

        {/* RIGHT RAIL */}
        <aside className="sf-rail">
          <div className="sf-panel ov">
            <div className="ovk">Overview · 概览</div>
            {[['话题', brief.topic], ['信源总数', m.total], ['精选', `${m.featured} 条`, true], ['时间跨度', m.window],
              ['社区共识', `${brief.consensus.left} / ${brief.consensus.right}`]].map(([l, v, blue]) => (
              <div className="row" key={l}><span className="l">{l}</span><span className={`v${blue ? ' blue' : ''}`}>{v}</span></div>
            ))}
          </div>

          <div className="sf-panel">
            <div className="ph"><h3>平台分布</h3><span className="meta">{m.total} 信源</span></div>
            <div className="stat3">
              {brief.dashboard.tiles.map(t => (
                <div className="stile" key={t.p}>
                  <div className="sp" style={{ color: PF(t.p).c }}><span className="d" style={{ background: PF(t.p).c }} />{t.label}</div>
                  <div className="big">{t.n}</div><div className="sub">{t.sub}</div>
                </div>
              ))}
            </div>
            <div className="blabel"><span>互动声量分布</span><span>总计 {brief.dashboard.volumeTotal}</span></div>
            <div className="stack">
              {brief.dashboard.volume.map(v => <span key={v.p} style={{ width: `${v.pct}%`, background: PF(v.p).c }} title={`${v.name} ${v.raw}`} />)}
            </div>
            <div className="legend">
              {brief.dashboard.volume.map(v => (
                <div className="lrow" key={v.p}><span className="ld" style={{ background: PF(v.p).c }} /><span className="ln">{v.name}</span><span className="pct">{v.pct}%</span><span className="raw">{v.raw}</span></div>
              ))}
            </div>
            {brief.dashboard.insight && <div className="insight" dangerouslySetInnerHTML={{ __html: richHtml(brief.dashboard.insight) }} />}
          </div>

          {has(brief.voices) && (
            <div className="sf-panel">
              <div className="ph"><h3>Top Voices</h3><span className="meta">{brief.voices.length} 节点</span></div>
              <div className="voices">{brief.voices.map(v => <span className="voice" key={v}>{v}</span>)}</div>
            </div>
          )}

          {brief.caveat && (
            <div className="sf-caveat">
              <div className="ct">⚠️ 数据缺口说明</div>
              <p dangerouslySetInnerHTML={{ __html: richHtml(brief.caveat) }} />
            </div>
          )}
        </aside>
      </div>
    </>
  )
}

function SecHead({ n, title, k }) {
  return <div className="sf-sechead"><span className="n">{n}</span><h2>{title}</h2><span className="ln" /><span className="k">{k}</span></div>
}

function renderHeadline(h) {
  if (!h) return ''
  const idx = h.lastIndexOf('，')
  if (idx < 0) return h
  return <>{h.slice(0, idx + 1)}<span className="mark">{h.slice(idx + 1)}</span></>
}

/* ============================ STYLES ============================ */
const STYLES = `
.sf-search{ --x:#15171a; --reddit:#ff4500; --hn:#ff6600; --teal:${TEAL}; --teal-soft:#eaf4ee; --teal-line:#cfe7da; --gold:${GOLD}; --gold-soft:#fbf1dc; --gold-line:#f0e0b8; --blue:var(--accent-blue); --blue-soft:var(--accent-blue-light); --line:var(--border); --paper-2:var(--bg-secondary); }
.sf-search ::selection{ background:#d9e6fc; }

.sf-appbar{ position:sticky; top:0; z-index:30; display:flex; align-items:center; gap:20px; padding:14px 46px; background:color-mix(in srgb, var(--bg-primary) 82%, transparent); backdrop-filter:saturate(140%) blur(10px); -webkit-backdrop-filter:saturate(140%) blur(10px); border-bottom:1px solid var(--border); }
.sf-ab-brand{ display:flex; align-items:center; gap:9px; font-size:15px; font-weight:700; letter-spacing:-.01em; flex:0 0 auto; color:var(--text-primary); }
.sf-ab-brand .m{ font-size:16px; }
.sf-ab-search{ flex:1; max-width:600px; display:flex; align-items:center; gap:10px; background:#fff; border:1.5px solid var(--accent-blue); border-radius:11px; height:44px; padding:0 14px; box-shadow:0 0 0 3px rgba(37,99,235,.07); }
.sf-ab-search .si{ color:var(--text-muted); font-size:15px; }
.sf-ab-search input{ flex:1; border:0; outline:0; background:transparent; font-size:14.5px; color:var(--text-primary); }
.sf-ab-search .clear{ color:var(--text-muted); cursor:pointer; font-size:14px; padding:3px; }
.sf-ab-search .clear:hover{ color:var(--text-secondary); }
.sf-ab-btn{ background:var(--accent-blue); color:#fff; border:0; border-radius:10px; height:44px; padding:0 22px; font-size:14.5px; font-weight:600; cursor:pointer; flex:0 0 auto; transition:background .12s; }
.sf-ab-btn:hover{ background:#1d4ed8; }
.sf-ab-btn:disabled{ opacity:.6; cursor:default; }

.sf-content{ padding:30px 46px 90px; max-width:1440px; }

/* empty / loading / error */
.sf-empty{ text-align:center; padding:120px 0; color:var(--text-muted); }
.sf-empty .ic{ font-size:46px; margin-bottom:16px; }
.sf-empty .t1{ font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:8px; }
.sf-empty .t2{ font-size:14px; max-width:520px; margin:0 auto; line-height:1.6; }
.sf-empty .t2.err{ color:#b91c1c; }
.sf-load{ display:flex; gap:6px; justify-content:center; margin-top:22px; }
.sf-load span{ width:8px; height:8px; border-radius:50%; background:var(--accent-blue); animation:sfBlink 1.2s infinite; }
.sf-load span:nth-child(2){ animation-delay:.2s; } .sf-load span:nth-child(3){ animation-delay:.4s; }

/* search history */
.sf-home{ max-width:680px; margin:0 auto; }
.sf-home .sf-empty{ padding:64px 0 28px; }
.sf-history{ margin-top:6px; }
.sf-history .hh{ display:flex; align-items:baseline; justify-content:space-between; margin:0 0 12px; }
.sf-history .hh h3{ font-size:13px; font-weight:700; color:var(--text-primary); margin:0; letter-spacing:.02em; }
.sf-history .hh .meta{ font-size:11px; color:var(--text-muted); }
.sf-history .hlist{ display:flex; flex-direction:column; gap:8px; }
.sf-history .hrow{ display:flex; align-items:center; gap:12px; width:100%; text-align:left; cursor:pointer;
  background:#fff; border:1px solid var(--border); border-radius:12px; padding:13px 16px; transition:all .12s; }
.sf-history .hrow:hover{ border-color:#cdd9f2; box-shadow:0 4px 14px rgba(37,99,235,.07); transform:translateY(-1px); }
.sf-history .hrow .ht{ font-size:14.5px; font-weight:600; color:var(--text-primary); flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.sf-history .hrow .hn{ font-size:11.5px; color:var(--text-secondary); background:var(--bg-secondary); border:1px solid var(--border); border-radius:6px; padding:2px 8px; flex:0 0 auto; }
.sf-history .hrow .hd{ font-size:11.5px; color:var(--text-muted); flex:0 0 auto; font-variant-numeric:tabular-nums; }
.sf-history .hrow .hgo{ color:var(--text-muted); flex:0 0 auto; }
.sf-history .hrow:hover .hgo{ color:#1d4fd7; }

/* result bar */
.sf-resultbar{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:30px; font-size:12.5px; color:var(--text-muted); }
.sf-resultbar .q{ font-size:15px; font-weight:700; color:var(--text-primary); }
.sf-resultbar .q em{ font-style:normal; color:var(--text-muted); font-weight:500; font-size:13px; margin-left:8px; }
.sf-resultbar b{ color:var(--text-primary); }
.sf-resultbar .dot{ width:3px; height:3px; border-radius:50%; background:var(--text-muted); }
.sf-resultbar .pill{ background:var(--bg-secondary); border:1px solid var(--border); border-radius:6px; padding:3px 9px; color:var(--text-secondary); }

/* layout */
.sf-layout{ display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:44px; align-items:start; }
@media (max-width:1180px){ .sf-layout{ grid-template-columns:1fr; } }
.sf-sec{ margin-top:54px; }
.sf-sec:first-child{ margin-top:0; }
.sf-sechead{ display:flex; align-items:baseline; gap:13px; margin:0 0 22px; }
.sf-sechead .n{ font-size:12px; font-weight:700; color:var(--accent-blue); letter-spacing:.04em; }
.sf-sechead h2{ font-size:21px; font-weight:800; letter-spacing:-.015em; margin:0; color:var(--text-primary); }
.sf-sechead .k{ font-size:11px; letter-spacing:.13em; color:var(--text-muted); text-transform:uppercase; }
.sf-sechead .ln{ flex:1; height:1px; background:var(--border); align-self:center; }

.sf-src{ color:#1d4fd7; font-weight:500; }
.sf-hl{ color:#1d4fd7; font-weight:600; }
.sf-q{ color:var(--text-primary); font-weight:500; border-bottom:1.5px solid #e6dfcb; padding-bottom:1px; }
.sf-num{ font-weight:700; color:var(--text-primary); }
.sf-mono{ font-size:12.5px; background:var(--bg-secondary); padding:1px 6px; border-radius:5px; }

.sf-hero{ border-bottom:1px solid var(--border); padding-bottom:30px; }
.sf-kicker{ display:flex; align-items:center; gap:9px; font-size:11.5px; letter-spacing:.1em; color:var(--text-muted); text-transform:uppercase; margin-bottom:16px; }
.sf-kicker .pulse{ width:7px; height:7px; border-radius:50%; background:var(--accent-blue); box-shadow:0 0 0 0 rgba(37,99,235,.5); animation:sfPulse 2s infinite; }
@keyframes sfPulse{ 0%{box-shadow:0 0 0 0 rgba(37,99,235,.45);} 70%{box-shadow:0 0 0 7px rgba(37,99,235,0);} 100%{box-shadow:0 0 0 0 rgba(37,99,235,0);} }
.sf-hero h1{ font-size:38px; line-height:1.12; font-weight:800; letter-spacing:-.03em; margin:0 0 16px; text-wrap:balance; color:var(--text-primary); }
.sf-hero h1 .mark{ background:linear-gradient(transparent 62%, #d9e6fc 62%); padding:0 2px; }
.sf-lede{ font-size:16.5px; line-height:1.6; color:var(--text-secondary); max-width:62ch; margin:0 0 26px; text-wrap:pretty; }
.sf-lede b{ color:var(--text-primary); font-weight:600; }
.sf-vbar-wrap{ max-width:560px; }
.sf-vbar-ends{ display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:8px; }
.sf-vbar-ends .e{ display:flex; flex-direction:column; gap:3px; }
.sf-vbar-ends .e.r{ text-align:right; }
.sf-vbar-ends .lab{ font-size:13.5px; font-weight:700; color:var(--text-primary); }
.sf-vbar-ends .meta{ font-size:11px; color:var(--text-muted); }
.sf-vbar{ position:relative; height:14px; border-radius:8px; overflow:hidden; display:flex; }
.sf-vbar .l{ background:var(--accent-blue); }
.sf-vbar .r{ background:#c9a24b; }
.sf-vbar .mid{ position:absolute; left:50%; top:-4px; bottom:-4px; width:2px; background:var(--bg-primary); transform:translateX(-50%); }
.sf-vbar-cap{ text-align:center; font-size:11.5px; color:var(--text-muted); margin-top:9px; }
.sf-vbar-cap b{ color:var(--text-primary); }

.sf-themes{ display:flex; flex-direction:column; gap:30px; }
.sf-theme{ display:grid; grid-template-columns:auto 1fr; gap:20px; align-items:start; }
.sf-theme .tnum{ font-size:13px; font-weight:700; color:var(--accent-blue); padding-top:3px; }
.sf-theme h3{ font-size:17px; font-weight:700; margin:0 0 9px; letter-spacing:-.01em; color:var(--text-primary); }
.sf-theme p{ margin:0; font-size:15.4px; line-height:1.74; color:var(--text-secondary); text-wrap:pretty; }
@media (max-width:560px){ .sf-theme{ grid-template-columns:1fr; gap:6px; } }

.sf-patterns{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width:560px){ .sf-patterns{ grid-template-columns:1fr; } }
.sf-pcard{ background:#fff; border:1px solid var(--border); border-radius:14px; padding:18px 18px 16px; position:relative; overflow:hidden; transition:border-color .14s, box-shadow .14s, transform .14s; }
.sf-pcard:hover{ border-color:#cdd9f2; box-shadow:0 6px 18px rgba(37,99,235,.07); transform:translateY(-2px); }
.sf-pcard .pn{ font-size:13px; font-weight:700; color:#fff; background:var(--text-primary); width:26px; height:26px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
.sf-pcard.lead .pn{ background:var(--accent-blue); }
.sf-pcard p{ font-size:14.4px; line-height:1.55; margin:13px 0 14px; color:var(--text-secondary); text-wrap:pretty; }
.sf-pcard .psrc{ display:inline-flex; align-items:center; gap:6px; font-size:11.5px; color:var(--text-muted); border-top:1px dashed var(--border); padding-top:11px; width:100%; }
.sf-pcard .psrc .tag{ color:#1d4fd7; font-weight:500; }
.sf-pcard .badge{ position:absolute; top:16px; right:0; background:var(--accent-blue-light); color:#1d4fd7; font-size:10px; letter-spacing:.08em; padding:3px 10px 3px 8px; border-radius:6px 0 0 6px; }

.sf-deep{ background:#fff; border:1px solid var(--border); border-radius:16px; padding:24px 26px; box-shadow:0 1px 3px rgba(40,35,20,.035); }
.sf-deep-sub{ font-size:13.5px; color:var(--text-muted); margin:0 0 16px; }
.sf-ditem{ border:1px solid var(--border); border-radius:11px; margin-bottom:10px; overflow:hidden; transition:border-color .14s; }
.sf-ditem.open{ border-color:#cdd9f2; }
.sf-ditem .dq{ display:flex; align-items:center; gap:13px; padding:15px 16px; cursor:pointer; font-size:14.5px; color:var(--text-secondary); transition:background .12s; }
.sf-ditem .dq:hover{ background:#f2f6fe; }
.sf-ditem.open .dq{ color:var(--text-primary); font-weight:600; }
.sf-ditem .da{ font-size:12px; color:#1d4fd7; background:var(--accent-blue-light); width:24px; height:24px; border-radius:7px; display:flex; align-items:center; justify-content:center; flex:0 0 auto; }
.sf-ditem .dchev{ margin-left:auto; color:var(--text-muted); font-size:13px; transition:transform .2s; flex:0 0 auto; }
.sf-ditem.open .dchev{ transform:rotate(90deg); color:#1d4fd7; }
.sf-ditem .danswer{ overflow:hidden; transition:max-height .32s ease; }
.sf-ditem .danswer-inner{ padding:2px 18px 18px 53px; font-size:13.8px; line-height:1.7; color:var(--text-secondary); }
.sf-ditem .danswer-inner b{ color:var(--text-primary); }
.sf-ditem .typing{ display:inline-flex; gap:4px; align-items:center; color:var(--text-muted); font-size:12px; }
.sf-ditem .typing .dot{ width:5px; height:5px; border-radius:50%; background:var(--accent-blue); animation:sfBlink 1.2s infinite; }
.sf-ditem .typing .dot:nth-child(2){ animation-delay:.2s; }
.sf-ditem .typing .dot:nth-child(3){ animation-delay:.4s; }
@keyframes sfBlink{ 0%,60%,100%{opacity:.25;} 30%{opacity:1;} }

.sf-tl-controls{ display:flex; align-items:center; gap:8px; margin:0 0 26px; flex-wrap:wrap; }
.sf-tlchip{ font-size:12px; padding:7px 13px; border-radius:9px; border:1px solid var(--border); background:#fff; color:var(--text-secondary); cursor:pointer; display:flex; align-items:center; gap:7px; white-space:nowrap; transition:all .12s; }
.sf-tlchip:hover{ border-color:#cfcabd; }
.sf-tlchip.on{ background:var(--text-primary); color:#fff; border-color:var(--text-primary); }
.sf-tlchip .c{ width:7px; height:7px; border-radius:2px; }
.sf-tlchip.feat.on{ background:var(--gold-soft); color:var(--gold); border-color:var(--gold-line); }
.sf-tl-count{ font-size:12px; color:var(--text-muted); margin-left:auto; white-space:nowrap; }
.sf-timeline{ position:relative; }
.sf-tl-group{ position:relative; }
.sf-tl-group::before{ content:""; position:absolute; left:74px; top:50px; bottom:6px; width:2px; background:var(--border); }
.sf-tl-group:last-child::before{ bottom:18px; }
.sf-tl-day{ display:flex; align-items:center; gap:11px; margin:4px 0 18px; }
.sf-tl-day .d{ font-weight:700; font-size:14px; color:var(--text-primary); }
.sf-tl-day .dn{ font-size:11.5px; color:var(--text-muted); }
.sf-tl-day .dln{ flex:1; height:1px; background:var(--border-light); }
.sf-tl-item{ display:flex; position:relative; padding-bottom:22px; }
.sf-tl-side{ flex:0 0 74px; width:74px; text-align:right; padding-right:26px; padding-top:17px; }
.sf-tl-side .t{ font-weight:700; font-size:14px; color:var(--text-primary); letter-spacing:-.02em; }
.sf-tl-side .ago{ font-size:10.5px; color:var(--text-muted); margin-top:3px; }
.sf-tl-dot{ position:absolute; left:74px; top:23px; width:11px; height:11px; border-radius:50%; background:#fff; border:2.5px solid var(--text-muted); transform:translateX(-50%); z-index:1; }
.sf-tl-item.feat .sf-tl-dot{ border-color:var(--accent-blue); background:var(--accent-blue); box-shadow:0 0 0 4px var(--accent-blue-light); }
.sf-tl-card{ flex:1; min-width:0; margin-left:30px; background:#fff; border:1px solid var(--border); border-radius:14px; padding:18px 20px; box-shadow:0 1px 3px rgba(40,35,20,.035); transition:border-color .14s, box-shadow .14s; }
.sf-tl-card:hover{ border-color:#cdd9f2; box-shadow:0 8px 24px rgba(37,99,235,.08); }
.sf-tl-card .top{ display:flex; align-items:center; gap:10px; margin-bottom:12px; }
.sf-tl-card .ava{ width:27px; height:27px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:#fff; flex:0 0 auto; letter-spacing:-.02em; }
.sf-tl-card .who{ font-size:13.5px; font-weight:600; color:var(--text-primary); }
.sf-tl-card .handle{ font-size:12px; color:var(--text-muted); }
.sf-tl-card .right{ margin-left:auto; display:flex; align-items:center; gap:8px; flex:0 0 auto; }
.sf-tl-card .feat-badge{ display:inline-flex; align-items:center; gap:5px; font-size:11px; font-weight:700; color:var(--gold); background:var(--gold-soft); border:1px solid var(--gold-line); border-radius:7px; padding:4px 9px; }
.sf-tl-card .score{ font-size:12px; font-weight:700; color:#1d4fd7; background:var(--accent-blue-light); border:1px solid #dce7fb; border-radius:7px; padding:4px 10px; min-width:34px; text-align:center; }
.sf-tl-card .score .sl{ font-size:9px; font-weight:500; color:var(--text-muted); margin-right:3px; }
.sf-tl-card .ttl{ display:block; font-size:16.5px; font-weight:700; letter-spacing:-.01em; line-height:1.4; margin-bottom:8px; color:var(--text-primary); text-wrap:pretty; text-decoration:none; }
.sf-tl-card a.ttl:hover{ color:#1d4fd7; }
.sf-tl-card .sum{ font-size:14px; line-height:1.68; color:var(--text-secondary); text-wrap:pretty; }
.sf-tl-card .tags{ display:flex; gap:7px; margin-top:14px; flex-wrap:wrap; align-items:center; }
.sf-tl-card .tags .tag{ font-size:11.5px; color:var(--text-secondary); background:var(--bg-secondary); border:1px solid var(--border); border-radius:6px; padding:3px 10px; }
.sf-tl-card .tags .stat{ font-size:11.5px; color:var(--text-muted); margin-left:auto; }
.sf-tl-card .reason{ margin-top:14px; display:flex; gap:11px; align-items:flex-start; background:var(--teal-soft); border:1px solid var(--teal-line); border-left:3px solid var(--teal); border-radius:9px; padding:12px 14px; }
.sf-tl-card .reason .rl{ font-size:11px; font-weight:700; color:var(--teal); flex:0 0 auto; letter-spacing:.03em; padding-top:2px; }
.sf-tl-card .reason p{ margin:0; font-size:13.4px; line-height:1.62; color:#2c5544; text-wrap:pretty; }
.sf-tl-end{ display:flex; align-items:center; gap:11px; margin-top:6px; padding-left:104px; }
.sf-tl-end .raw{ font-size:11.5px; color:var(--text-muted); }

.sf-rail{ position:sticky; top:78px; display:flex; flex-direction:column; gap:18px; }
@media (max-width:1180px){ .sf-rail{ position:static; } }
.sf-panel{ background:#fff; border:1px solid var(--border); border-radius:16px; padding:20px; box-shadow:0 1px 3px rgba(40,35,20,.035); }
.sf-panel .ph{ display:flex; align-items:center; justify-content:space-between; margin-bottom:15px; }
.sf-panel .ph h3{ font-size:14px; font-weight:700; margin:0; color:var(--text-primary); }
.sf-panel .ph .meta{ font-size:11px; color:var(--text-muted); }
.sf-panel.ov{ background:var(--text-primary); border:0; }
.sf-panel.ov .ovk{ font-size:11px; letter-spacing:.1em; color:#a8a39a; text-transform:uppercase; margin-bottom:14px; }
.sf-panel.ov .row{ display:flex; justify-content:space-between; align-items:baseline; padding:9px 0; border-top:1px solid rgba(255,255,255,.1); }
.sf-panel.ov .row:first-of-type{ border-top:0; }
.sf-panel.ov .l{ font-size:13px; color:#c9c5bc; }
.sf-panel.ov .v{ font-size:14px; font-weight:700; color:#fff; }
.sf-panel.ov .v.blue{ color:#7fa9fb; }
.sf-panel .stat3{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:9px; margin-bottom:16px; }
.sf-panel .stile{ border:1px solid var(--border); border-radius:11px; padding:11px 11px 10px; }
.sf-panel .stile .sp{ display:flex; align-items:center; gap:6px; font-size:10px; font-weight:700; letter-spacing:.04em; }
.sf-panel .stile .sp .d{ width:8px; height:8px; border-radius:3px; }
.sf-panel .stile .big{ font-size:21px; font-weight:800; letter-spacing:-.02em; margin-top:8px; line-height:1; color:var(--text-primary); }
.sf-panel .stile .sub{ font-size:10px; color:var(--text-muted); margin-top:5px; }
.sf-panel .blabel{ display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin-bottom:8px; }
.sf-panel .stack{ display:flex; height:13px; border-radius:7px; overflow:hidden; background:var(--bg-secondary); margin-bottom:10px; }
.sf-panel .stack span{ height:100%; }
.sf-panel .legend{ display:flex; flex-direction:column; gap:7px; }
.sf-panel .lrow{ display:flex; align-items:center; gap:8px; font-size:12.5px; color:var(--text-secondary); }
.sf-panel .lrow .ld{ width:9px; height:9px; border-radius:3px; flex:0 0 auto; }
.sf-panel .lrow .ln{ font-weight:600; }
.sf-panel .lrow .pct{ margin-left:auto; font-size:12px; color:var(--text-primary); font-weight:700; }
.sf-panel .lrow .raw{ font-size:11px; color:var(--text-muted); width:62px; text-align:right; }
.sf-panel .insight{ margin-top:14px; font-size:12.6px; line-height:1.55; color:var(--text-secondary); background:#f2f6fe; border:1px solid #e0eafb; border-radius:9px; padding:11px 12px; }
.sf-panel .insight b{ color:#1d4fd7; }
.sf-panel .voices{ display:flex; flex-wrap:wrap; gap:7px; }
.sf-panel .voice{ font-size:12px; padding:5px 11px; border-radius:999px; border:1px solid var(--border); color:var(--text-secondary); background:var(--bg-secondary); cursor:pointer; transition:all .12s; }
.sf-panel .voice:hover{ border-color:var(--accent-blue); color:#1d4fd7; background:#f2f6fe; }
.sf-caveat{ background:#fbf1e2; border:1px solid #f0e0c5; border-radius:16px; padding:18px 20px; }
.sf-caveat .ct{ display:flex; align-items:center; gap:8px; font-size:13.5px; font-weight:700; color:#b5701b; margin-bottom:8px; }
.sf-caveat p{ margin:0; font-size:13px; line-height:1.6; color:#7a5c2e; }
.sf-caveat .sf-mono{ background:#f4e7d0; color:#8a5a12; }

@media (max-width:680px){
  .sf-appbar{ padding:12px 18px; gap:12px; }
  .sf-content{ padding:24px 18px 70px; }
  .sf-hero h1{ font-size:29px; }
  .sf-tl-side{ flex:0 0 58px; width:58px; padding-right:16px; }
  .sf-tl-group::before, .sf-tl-dot{ left:58px; }
  .sf-tl-card{ margin-left:22px; }
  .sf-tl-end{ padding-left:0; flex-wrap:wrap; }
}
`
