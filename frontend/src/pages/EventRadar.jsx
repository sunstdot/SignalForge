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
    <div className="text-xs mt-2" style={{ color: 'var(--text-secondary)' }}>
      <strong>{label}：</strong>
      {status !== 'found' || posts.length === 0 ? STATUS_NAMES[status] || '检索不可用' : (
        <ul className="list-disc pl-5 mt-1">
          {posts.map((post, index) => (
            <li key={`${name}-${post.url || index}`}>
              {safeUrl(post.url) ? (
                <a href={safeUrl(post.url)} target="_blank" rel="noopener noreferrer" className="hover:underline"
                  style={{ color: 'var(--accent-blue)' }}>{post.title || `查看 ${label} 原帖`}</a>
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
    <div className="space-y-4">
      <h3 className="font-semibold text-base" style={{ color: 'var(--text-primary)' }}>事件追踪</h3>
      {unavailable && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
        部分发现信源采集不可用；以下仅代表已取得的内容。
      </p>}
      {selectionStatus === 'unavailable' && <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
        本日事件筛选不可用；原始内容仍可在「全部内容」查看。
      </p>}
      {selectionStatus === 'not_run' && <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
        事件筛选尚未运行；只完成了信源采集，可在「全部内容」查看原始条目。
      </p>}
      {events.length === 0 && !['unavailable', 'not_run'].includes(selectionStatus) && <p className="text-sm py-6" style={{ color: 'var(--text-muted)' }}>
        今天没有足够原始依据的具体事件；不会用其他话题凑数。
      </p>}
      {events.map(event => (
        <article key={event.id} className="rounded-lg border p-4" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{event.title}</h3>
          {event.progress && <span className="text-xs" style={{ color: 'var(--accent-blue)' }}>新增进展</span>}
          <p className="text-sm mt-3" style={{ color: 'var(--text-secondary)' }}>
            <strong>发生了什么：</strong>{event.what_happened}
          </p>
          <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>
            <strong>值得看什么：</strong>{event.why_read}
          </p>
          <div className="mt-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <strong>原始信源：</strong>
            <ul className="list-disc pl-5 mt-1">
              {(event.sources || []).map((source, index) => (
                <li key={`${event.id}-source-${source.id || index}`}>
                  {safeUrl(source.url) ? <a href={safeUrl(source.url)} target="_blank" rel="noopener noreferrer"
                    className="hover:underline" style={{ color: 'var(--accent-blue)' }}>{source.title || source.source || '查看原文'}</a>
                    : source.title || source.source || '原文链接不可用'}
                  {source.source && <span> · {source.source}</span>}
                </li>
              ))}
            </ul>
          </div>
          <div className="mt-3 border-t pt-2" style={{ borderColor: 'var(--border)' }}>
            {Object.keys(PLATFORM_NAMES).map(name => <Discussion key={name} name={name} result={event.discussions?.[name]} />)}
          </div>
        </article>
      ))}
    </div>
  )
}
