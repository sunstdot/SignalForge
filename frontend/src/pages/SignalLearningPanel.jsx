import { useEffect, useState } from 'react'

const VERDICTS = [
  { key: 'matched', label: '符合预期' },
  { key: 'topic_only', label: '主题相似，但没有同样的价值' },
  { key: 'irrelevant', label: '不相关' },
]

function SearchStatus({ similar }) {
  if (!similar) return null
  if (similar.status === 'ok') {
    return <p className="sl-status sl-status-ok">试找完成：找到 {similar.found} 条类似内容。</p>
  }
  if (similar.status === 'no_match') {
    return (
      <>
        <p className="sl-status sl-status-warn">检索成功，但没有找到符合价值特征的类似内容（没有用低质量内容凑数）。</p>
        {similar.suggestion && <p className="sl-hint">{similar.suggestion}</p>}
      </>
    )
  }
  return <p className="sl-status sl-status-error">检索失败：{similar.search_error || similar.error || similar.status}。已保存的样本与学习结果不受影响。</p>
}

function RecommendationCard({ rec, referenceId, onFeedback }) {
  const [verdict, setVerdict] = useState(null)
  const match = rec.match || {}
  return (
    <article className="sl-rec">
      <a href={rec.url} target="_blank" rel="noopener noreferrer" className="sl-rec-title">{rec.title}</a>
      <p className="sl-rec-reason">{rec.recommend_reason}</p>
      {match.similarity === 'topic' && <p className="sl-rec-topic">仅主题相似，未发现相同的价值特征。</p>}
      <div className="sl-rec-actions" role="group" aria-label="对推荐结果反馈">
        {verdict ? (
          <span className="sl-rec-done">已记录：{VERDICTS.find(v => v.key === verdict)?.label}</span>
        ) : VERDICTS.map(v => (
          <button key={v.key} type="button" className="sl-btn sl-btn-ghost"
            onClick={async () => { await onFeedback(referenceId, v.key); setVerdict(v.key) }}>
            {v.label}
          </button>
        ))}
      </div>
    </article>
  )
}

export default function SignalLearningPanel({ onChanged }) {
  const [url, setUrl] = useState('')
  const [reason, setReason] = useState('')
  const [wants, setWants] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [references, setReferences] = useState([])
  const [preferences, setPreferences] = useState(null)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null) // ref id being edited

  async function reload() {
    try {
      const [refs, prefs] = await Promise.all([
        fetch('/api/signal-learning/references').then(r => r.ok ? r.json() : { references: [] }),
        fetch('/api/signal-learning/preferences').then(r => r.ok ? r.json() : null),
      ])
      setReferences(refs.references || [])
      setPreferences(prefs)
    } catch { /* 后端不可用时保持现状 */ }
  }

  useEffect(() => { reload() }, [])

  async function submit() {
    if (!url.trim()) return
    setSubmitting(true)
    setError('')
    setLastResult(null)
    try {
      const res = await fetch('/api/signal-learning/references', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim(), user_reason: reason.trim(), user_wants: wants.trim() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '提交失败')
      setLastResult(data)
      setUrl(''); setReason(''); setWants('')
      reload()
      onChanged?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function act(refId, action, body) {
    const init = action === 'update'
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      : { method: action === 'delete' ? 'DELETE' : 'POST' }
    const res = await fetch(`/api/signal-learning/references/${refId}${action === 'delete' ? '' : '/' + action}`, init)
    if (res.ok) { setEditing(null); reload(); onChanged?.() }
  }

  async function sendFeedback(refId, verdict, index) {
    await fetch(`/api/signal-learning/references/${refId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index, verdict }),
    })
  }

  const analysis = lastResult?.reference?.analysis
  const activeRefs = references.filter(r => r.status === 'active')

  return (
    <div className="sl-panel" aria-label="参考信息学习">
      <div className="sl-form">
        <h3>用这条信息，帮我发现更多</h3>
        <p className="sl-hint">提供一条你觉得有价值的参考链接，系统会提取它的价值特征，并用这些特征持续寻找类似信息。不填原因也可以。</p>
        <input type="url" className="sl-input" placeholder="参考链接（必填）" value={url}
          onChange={e => setUrl(e.target.value)} aria-label="参考链接" />
        <textarea className="sl-input sl-textarea" placeholder="为什么觉得有用？（选填，填了会以你写的为准）" value={reason}
          onChange={e => setReason(e.target.value)} aria-label="为什么觉得有用" rows={2} />
        <textarea className="sl-input sl-textarea" placeholder="希望继续看到什么？（选填）" value={wants}
          onChange={e => setWants(e.target.value)} aria-label="希望继续看到什么" rows={2} />
        <div className="sl-form-actions">
          <button type="button" className="sl-btn sl-btn-primary" disabled={submitting || !url.trim()} onClick={submit}>
            {submitting ? '分析中（读取内容并试找，可能需要一两分钟）…' : '添加参考信息'}
          </button>
        </div>
        {error && <p className="sl-status sl-status-error">{error}</p>}
      </div>

      {lastResult && (
        <div className="sl-result">
          <div className="sl-result-states">
            <span className={`sl-chip ${lastResult.sample_saved ? 'ok' : 'error'}`}>{lastResult.sample_saved ? '样本已保存' : '样本保存失败'}</span>
            <span className={`sl-chip ${lastResult.analysis_complete ? 'ok' : 'warn'}`}>
              {lastResult.analysis_complete ? '内容分析完成' : `分析不完整：${lastResult.analysis_error || lastResult.fetch_reason || '正文缺失'}`}
            </span>
            <span className={`sl-chip ${lastResult.learning_active ? 'ok' : 'warn'}`}>{lastResult.learning_active ? '学习结果已生效' : '学习未生效'}</span>
          </div>
          {!lastResult.fetch_ok && (
            <p className="sl-status sl-status-warn">原文未能完整获取（{lastResult.fetch_reason}）。已保留缺失状态，未根据标题补写事实；你可以把正文或关键上下文补充进「为什么觉得有用」。</p>
          )}
          {analysis && (
            <div className="sl-learned">
              <h4>从这条信息中学到了什么</h4>
              <dl className="sl-dl">
                <div><dt>主题</dt><dd>{analysis.topic}</dd></div>
                <div><dt>场景</dt><dd>{analysis.scenario}</dd></div>
                <div><dt>信息贡献</dt><dd>{analysis.contribution}</dd></div>
                <div><dt>价值原因</dt><dd>{analysis.value_reason}
                  {analysis.value_reason_source === 'inferred'
                    ? <em className="sl-inferred">（系统推测，不是你表达的偏好）</em>
                    : <em className="sl-user">（来自你填写的原因）</em>}
                </dd></div>
                <div><dt>证据形态</dt><dd>{(analysis.evidence_forms || []).join('、') || '未识别'}</dd></div>
                {analysis.uncertain && <div><dt>仍不确定</dt><dd>{analysis.uncertain}</dd></div>}
              </dl>
              {(analysis.search_clues || []).length > 0 && (
                <>
                  <h4>后续会沿这些方向寻找</h4>
                  <ul className="sl-clues">
                    {analysis.search_clues.map((c, i) => (
                      <li key={i}>「{c.query}」{c.subreddits?.length ? ` · r/${c.subreddits.join(', r/')}` : ''}{c.handles?.length ? ` · @${c.handles.join(', @')}` : ''}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}
          {lastResult.similar && (
            <div className="sl-similar">
              <h4>立即试找的类似信息（最多 3 条）</h4>
              <SearchStatus similar={lastResult.similar} />
              {(lastResult.similar.recommendations || []).map((rec, i) => (
                <RecommendationCard key={rec.id || i} rec={rec} referenceId={lastResult.sample_id}
                  onFeedback={(refId, verdict) => sendFeedback(refId, verdict, i)} />
              ))}
              {lastResult.similar.inferred_reason && (
                <p className="sl-hint">你没有填写原因，以上方向基于系统推测；如果方向不对，可以修改或停用这条学习结果。</p>
              )}
            </div>
          )}
        </div>
      )}

      {references.length > 0 && (
        <div className="sl-refs">
          <h4>已保存的参考样本（{activeRefs.length} 生效中）</h4>
          {preferences?.active_references?.length > 0 && (
            <p className="sl-hint">
              当前生效偏好：
              {preferences.themes.length > 0 && `主题 ${preferences.themes.map(t => t.text).slice(0, 3).join('、')}`}
              {preferences.value_patterns.length > 0 && ` · 价值特征 ${preferences.value_patterns.map(p => p.form).join('、')}`}
            </p>
          )}
          {references.map(ref => (
            <div key={ref.id} className={`sl-ref ${ref.status === 'disabled' ? 'sl-ref-disabled' : ''}`}>
              <div className="sl-ref-head">
                <a href={ref.url} target="_blank" rel="noopener noreferrer">{ref.title}</a>
                <span className={`sl-chip ${ref.status === 'active' ? 'ok' : 'muted'}`}>{ref.status === 'active' ? '生效中' : '已停用'}</span>
                {ref.last_similar && (
                  <span className="sl-ref-last">上次试找：{ref.last_similar.search_status === 'ok' ? `找到 ${ref.last_similar.found} 条` : ref.last_similar.search_status}</span>
                )}
              </div>
              {ref.analysis && <p className="sl-ref-analysis">{ref.analysis.topic} · {ref.analysis.contribution}</p>}
              {editing === ref.id ? (
                <div className="sl-ref-edit">
                  <textarea className="sl-input sl-textarea" defaultValue={ref.user_reason} rows={2}
                    aria-label="修改原因" id={`sl-edit-${ref.id}`} />
                  <div className="sl-form-actions">
                    <button type="button" className="sl-btn sl-btn-primary"
                      onClick={() => act(ref.id, 'update', { user_reason: document.getElementById(`sl-edit-${ref.id}`).value })}>保存并重学</button>
                    <button type="button" className="sl-btn sl-btn-ghost" onClick={() => setEditing(null)}>取消</button>
                  </div>
                </div>
              ) : (
                <div className="sl-ref-actions">
                  <button type="button" className="sl-btn sl-btn-ghost" onClick={() => setEditing(ref.id)}>修改原因</button>
                  {ref.status === 'active'
                    ? <button type="button" className="sl-btn sl-btn-ghost" onClick={() => act(ref.id, 'disable')}>停用</button>
                    : <button type="button" className="sl-btn sl-btn-ghost" onClick={() => act(ref.id, 'enable')}>重新启用</button>}
                  <button type="button" className="sl-btn sl-btn-danger" onClick={() => act(ref.id, 'delete')}>撤销</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
