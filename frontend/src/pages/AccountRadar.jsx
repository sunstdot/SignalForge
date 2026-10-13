import React from 'react'
import ReactMarkdown from 'react-markdown'

function safeUrl(value) {
  try {
    const parsed = new URL(value)
    return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : null
  } catch {
    return null
  }
}

export default function AccountRadar({ accounts }) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-base" style={{ color: 'var(--text-primary)' }}>关注账号</h3>
      {accounts.length === 0 && <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
        尚未保存账号采集结果，不会以话题搜索结果替代账号动态。
      </p>}
      {accounts.map(account => (
        <section key={account.handle} className="rounded-lg border p-4" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{account.handle}</h4>
            {account.checked_at && <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              检查于 {account.checked_at.slice(0, 16).replace('T', ' ')} UTC
            </span>}
          </div>
          {account.status === 'unavailable' && <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>
            账号采集不可用；不能据此推断今天没有发帖。
          </p>}
          {account.status === 'partial' && <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>
            覆盖不完整：仅包含公开页面可核验的近期帖文，不代表完整时间线。
          </p>}
          {account.status === 'ok' && account.posts.length === 0 && <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>
            本次公开页面确认没有可见的近期帖文；不代表其他渠道完全没有。
          </p>}
          {account.status === 'partial' && account.posts.length === 0 && <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>
            本次未取得可核验的原创或引用帖，不能当作账号未发帖。
          </p>}
          {(account.posts || []).map(post => (
            <article key={post.id} className="mt-4 border-t pt-3" style={{ borderColor: 'var(--border)' }}>
              <div className="flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                <span>{post.kind === 'quote' ? '引用帖' : '原创'}</span>
                {post.published_at && <span>· {post.published_at.slice(0, 16).replace('T', ' ')} UTC</span>}
              </div>
              <p className="font-medium mt-2" style={{ color: 'var(--text-primary)' }}>{post.title}</p>
              {post.takeaway && <div className="text-sm mt-2 markdown-content" style={{ color: 'var(--text-secondary)' }}>
                <strong>{post.text_type === 'quick_read' ? '已有速读：' : '原文摘录：'}</strong>
                <ReactMarkdown>{post.takeaway}</ReactMarkdown>
              </div>}
              <div className="flex flex-wrap gap-4 text-xs mt-3">
                {safeUrl(post.url) && <a href={safeUrl(post.url)} target="_blank" rel="noopener noreferrer"
                  style={{ color: 'var(--accent-blue)' }}>查看原帖 ↗</a>}
                {post.kind === 'quote' && safeUrl(post.quoted_url) && <a href={safeUrl(post.quoted_url)}
                  target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-blue)' }}>查看被引用原帖 ↗</a>}
              </div>
            </article>
          ))}
        </section>
      ))}
    </div>
  )
}
