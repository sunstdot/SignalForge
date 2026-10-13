import React from 'react'

const PLATFORM_NAMES = { x: 'X', hn: 'HN', reddit: 'Reddit' }
const STATUS_NAMES = {
  no_results: '检索成功，未找到讨论',
  unavailable: '检索不可用',
  partial: '覆盖不完整',
}

function safeUrl(value) {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

function Discussion({ name, result }) {
  const label = PLATFORM_NAMES[name]
  const posts = Array.isArray(result?.posts) ? result.posts : []
  const status = result?.status || 'unavailable'
  return (
    <div className={`briefing-discussion briefing-discussion--${status}`} aria-label={`${label} 讨论`}>
      <strong>{label}</strong>
      {status !== 'found' || posts.length === 0 ? <span>{STATUS_NAMES[status] || '检索不可用'}</span> : (
        <ul>
          {posts.map((post, index) => (
            <li key={`${name}-${post.url || index}`}>
              {safeUrl(post.url) ? (
                <a href={safeUrl(post.url)} target="_blank" rel="noopener noreferrer">
                  {post.title || `查看 ${label} 原帖`}
                </a>
              ) : <span>{post.title || '原帖链接不可用'}</span>}
              {post.author && <span> · {post.author}</span>}
              {post.published_at && <span> · {post.published_at.slice(0, 10)}</span>}
              {post.engagement && <span> · {Object.entries(post.engagement).map(([key, value]) => `${value} ${key}`).join(', ')}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function EventRadar({ events, sourceStatus, selectionStatus }) {
  const unavailable = sourceStatus?.hn === 'unavailable' ||
    Object.values(sourceStatus?.reddit || {}).some(status => status === 'unavailable')
  return (
    <section className="briefing-events" aria-label="事件追踪">
      <header className="briefing-section-heading">
        <h3>事件追踪</h3>
        <span>{events.length} 件</span>
      </header>
      {unavailable && <p className="briefing-coverage-note">
        部分发现信源采集不可用；以下仅代表已取得的内容。
      </p>}
      {selectionStatus === 'unavailable' && <p className="briefing-empty">
        本日事件筛选不可用；原始内容仍可在「全部内容」查看。
      </p>}
      {selectionStatus === 'not_run' && <p className="briefing-empty">
        事件筛选尚未运行；只完成了信源采集，可在「全部内容」查看原始条目。
      </p>}
      {events.length === 0 && !['unavailable', 'not_run'].includes(selectionStatus) && <p className="briefing-empty">
        今天没有足够原始依据的具体事件；不会用其他话题凑数。
      </p>}
      {events.map(event => (
        <article key={event.id} className="briefing-event">
          <div className="briefing-event-headline">
            <h4>{event.title}</h4>
            {event.progress && <span className="briefing-progress">新增进展</span>}
          </div>
          <p className="briefing-event-fact"><strong>发生了什么：</strong>{event.what_happened}</p>
          <p className="briefing-event-context"><strong>值得看什么：</strong>{event.why_read}</p>
          <div className="briefing-event-sources">
            <strong>原始信源</strong>
            <ul>{(event.sources || []).map((source, index) => (
              <li key={`${event.id}-source-${source.id || index}`}>
                {safeUrl(source.url) ? <a href={safeUrl(source.url)} target="_blank" rel="noopener noreferrer">
                  {source.title || source.source || '查看原文'}
                </a> : source.title || source.source || '原文链接不可用'}
                {source.source && <span> · {source.source}</span>}
              </li>
            ))}</ul>
          </div>
          <div className="briefing-event-discussions" aria-label="跨平台讨论">
            {Object.keys(PLATFORM_NAMES).map(name => <Discussion key={name} name={name} result={event.discussions?.[name]} />)}
          </div>
        </article>
      ))}
    </section>
  )
}
