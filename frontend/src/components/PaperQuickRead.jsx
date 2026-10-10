import { useEffect, useId, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './PaperQuickRead.css'

export default function PaperQuickRead({ item }) {
  const dialogRef = useRef(null)
  const requestRef = useRef(null)
  const headingId = useId()
  const [state, setState] = useState('idle')
  const [summary, setSummary] = useState('')
  const [error, setError] = useState('')
  const isStatic = import.meta.env.VITE_STATIC_DATA === '1'

  useEffect(() => () => requestRef.current?.abort(), [])

  async function generate() {
    if (requestRef.current) return
    const controller = new AbortController()
    requestRef.current = controller
    setState('loading')
    setError('')
    try {
      const response = await fetch('/api/content/paper-quick-read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: item.id }),
        signal: controller.signal,
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : `论文速读请求失败（HTTP ${response.status}），请重试。`)
      }
      if (typeof data.summary !== 'string' || !data.summary.trim()) {
        throw new Error('未收到论文速读结果，请重新生成。')
      }
      setSummary(data.summary)
      setState('done')
    } catch (err) {
      if (err.name === 'AbortError') return
      setError(err instanceof TypeError ? '无法连接论文速读服务，请检查网络后重试。' : err.message)
      setState('error')
    } finally {
      if (requestRef.current === controller) requestRef.current = null
    }
  }

  function open() {
    dialogRef.current.showModal()
    if (state === 'idle') generate()
  }

  return (
    <>
      <button
        type="button"
        className="paper-read-button"
        onClick={open}
        disabled={isStatic}
        title={isStatic ? '请在连接后端服务的本地应用中使用论文速读' : '分析论文贡献、证据与适用边界'}
      >
        论文速读
      </button>
      <dialog ref={dialogRef} className="paper-read-dialog" aria-labelledby={headingId}>
        <div className="paper-read-header">
          <div className="paper-read-heading">
            <h2 id={headingId}>论文速读</h2>
            <p>{item.title}</p>
          </div>
          <button type="button" className="paper-read-close" aria-label="关闭论文速读" onClick={() => dialogRef.current.close()} autoFocus>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
        <div className="paper-read-body" aria-busy={state === 'loading'}>
          {state === 'loading' && (
            <div className="paper-read-status" role="status">
              <p>正在读取论文并生成速读…</p>
              <p>梳理核心贡献、关键假设与实验证据，可能需要几分钟。你可以先关闭弹窗，稍后再打开。</p>
            </div>
          )}
          {state === 'error' && (
            <div className="paper-read-status">
              <p role="alert">{error}</p>
              <button type="button" className="paper-read-button" onClick={generate}>重新生成</button>
            </div>
          )}
          {state === 'done' && (
            <div className="markdown-content paper-read-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
            </div>
          )}
        </div>
        <div className="paper-read-footer">
          <span>贡献 · 证据 · 适用边界</span>
          <a href={item.url} target="_blank" rel="noopener noreferrer">阅读原文 →</a>
        </div>
      </dialog>
    </>
  )
}
