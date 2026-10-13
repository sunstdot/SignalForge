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
    <section id="briefing-following" className="briefing-accounts" aria-label="关注账号">
      <header className="briefing-section-heading">
        <h3>关注账号</h3>
        <span>{accounts.length} 个账号</span>
      </header>
      {accounts.length === 0 && <p className="briefing-empty">
        尚未保存账号采集结果，不会以话题搜索结果替代账号动态。
      </p>}
      {accounts.map(account => (
        <section key={account.handle} className="briefing-account">
          <div className="briefing-account-heading">
            <h4>{account.handle}</h4>
            <span className={`briefing-account-status briefing-account-status--${account.status}`}>
              {account.status === 'unavailable' ? '不可用' : account.status === 'partial' ? '部分覆盖' : '已核验'}
            </span>
          </div>
          {account.status === 'unavailable' && <p className="briefing-account-note">
            账号采集不可用；不能据此推断今天没有发帖。
          </p>}
          {account.status === 'partial' && <p className="briefing-account-note">
            覆盖不完整：仅包含公开页面可核验的近期帖文，不代表完整时间线。
          </p>}
          {account.status === 'ok' && account.posts.length === 0 && <p className="briefing-account-note">
            本次公开页面确认没有可见的近期帖文；不代表其他渠道完全没有。
          </p>}
          {account.status === 'partial' && account.posts.length === 0 && <p className="briefing-account-note">
            本次未取得可核验的原创或引用帖，不能当作账号未发帖。
          </p>}
          {(account.posts || []).map(post => (
            <article key={post.id} className="briefing-account-post">
              <div className="briefing-post-meta">
                <span>{post.kind === 'quote' ? '引用帖' : '原创'}</span>
                {post.published_at && <time dateTime={post.published_at}>
                  {post.published_at.slice(0, 16).replace('T', ' ')} UTC
                </time>}
              </div>
              <p className="briefing-post-title">{post.title}</p>
              {post.takeaway && <div className="briefing-post-excerpt markdown-content">
                <strong>{post.text_type === 'quick_read' ? '已有速读：' : '原文摘录：'}</strong>
                <ReactMarkdown>{post.takeaway}</ReactMarkdown>
              </div>}
              <div className="briefing-post-links">
                {safeUrl(post.url) && <a href={safeUrl(post.url)} target="_blank" rel="noopener noreferrer">查看原帖 ↗</a>}
                {post.kind === 'quote' && safeUrl(post.quoted_url) && <a href={safeUrl(post.quoted_url)}
                  target="_blank" rel="noopener noreferrer">查看被引用原帖 ↗</a>}
              </div>
            </article>
          ))}
          {account.checked_at && <p className="briefing-account-checked">
            检查于 {account.checked_at.slice(0, 16).replace('T', ' ')} UTC
          </p>}
        </section>
      ))}
    </section>
  )
}
