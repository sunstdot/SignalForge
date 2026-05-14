import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function ExperimentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [experiment, setExperiment] = useState(null)
  const [logs, setLogs] = useState([])
  const [idea, setIdea] = useState(null)
  const [productConcept, setProductConcept] = useState(null) // { content, generated_at }
  const [newLog, setNewLog] = useState('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetchExperiment()
    fetchLogs()
  }, [id])

  const fetchExperiment = () => {
    setLoading(true)
    fetch(`/api/experiments/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Not found')
        return res.json()
      })
      .then(data => {
        setExperiment(data)
        setLoading(false)
        // 恢复已缓存的产品思路
        if (data.product_concept?.content) {
          setProductConcept(data.product_concept)
        }
        // Load linked idea for product concept context
        if (data.idea_id) {
          fetch(`/api/experiments/ideas/${data.idea_id}`)
            .then(r => r.ok ? r.json() : null)
            .then(ideaData => { if (ideaData) setIdea(ideaData) })
            .catch(() => { })
        }
      })
      .catch(() => {
        setLoading(false)
      })
  }

  const fetchLogs = () => {
    fetch(`/api/experiments/${id}/logs`)
      .then(res => res.json())
      .then(data => setLogs(data.logs || []))
  }

  const updateStatus = (status) => {
    fetch(`/api/experiments/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    })
      .then(res => res.json())
      .then(data => setExperiment(data))
  }

  const deleteExperiment = () => {
    if (!confirm('确定要删除这个实验吗？')) return

    fetch(`/api/experiments/${id}`, { method: 'DELETE' })
      .then(() => navigate('/experiments'))
  }

  const addLog = (e) => {
    e.preventDefault()
    if (!newLog.trim()) return

    fetch(`/api/experiments/${id}/logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: newLog })
    })
      .then(() => {
        setNewLog('')
        fetchLogs()
      })
  }

  const copyVibeCodingPrompt = () => {
    const prompt = `# Vibe Coding 启动指令

## 项目：${experiment.title}

${experiment.description ? `## 背景\n${experiment.description}\n` : ''}
## 产品方案

${productConcept.content}

---

## 开始实现

请基于以上产品方案开始实现这个项目。建议步骤：
1. 确认技术栈和项目结构
2. 搭建基础框架
3. 逐步实现核心功能（按产品方案中的优先级）
4. 每完成一个里程碑，告知进展

请从第一步开始。`

    navigator.clipboard.writeText(prompt).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const generateIdeas = () => {
    setGenerating(true)
    fetch(`/api/experiments/${id}/ideas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: experiment?.description || '' })
    })
      .then(res => res.json())
      .then(data => {
        setProductConcept({ content: data.ideas, generated_at: new Date().toISOString() })
        setGenerating(false)
      })
      .catch(() => setGenerating(false))
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return { bg: '#dcfce7', text: '#16a34a', border: '#86efac' }
      case 'in_progress': return { bg: '#dbeafe', text: '#2563eb', border: '#93c5fd' }
      case 'pending': return { bg: '#f3f4f6', text: '#6b7280', border: '#d1d5db' }
      default: return { bg: '#f3f4f6', text: '#6b7280', border: '#d1d5db' }
    }
  }

  const getStatusText = (status) => {
    switch (status) {
      case 'completed': return '已完成'
      case 'in_progress': return '进行中'
      case 'pending': return '待开始'
      default: return status
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
          <span className="loading-pulse">▌</span>
          <span className="text-sm">加载中...</span>
        </div>
      </div>
    )
  }

  if (!experiment) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <span className="text-3xl block mb-2">∅</span>
          <p className="text-red-600 mb-2">实验未找到</p>
          <Link to="/experiments" style={{ color: 'var(--accent-blue)' }} className="text-sm">
            返回实验列表
          </Link>
        </div>
      </div>
    )
  }

  const statusStyle = getStatusColor(experiment.status)

  return (
    <>
      {/* Top Bar */}
      <header
        className="sticky top-0 z-20 border-b px-4 py-3"
        style={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="window-dots">
              <span className="window-dot window-dot-red" />
              <span className="window-dot window-dot-yellow" />
              <span className="window-dot window-dot-green" />
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Link to="/" style={{ color: 'var(--text-muted)' }}>TokenBurner</Link>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <Link to="/experiments/live" style={{ color: 'var(--text-muted)' }}>实验直播场</Link>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span style={{ color: 'var(--accent-blue)' }} className="font-medium">
                {experiment.title}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
              <span>ID: {experiment.id.slice(0, 8)}...</span>
              <span
                className="px-1.5 py-0.5 rounded"
                style={{ backgroundColor: statusStyle.bg, color: statusStyle.text }}
              >
                {getStatusText(experiment.status)}
              </span>
              <span>创建: {new Date(experiment.created_at).toLocaleDateString()}</span>
              <span>日志: {logs.length}</span>
            </div>
            <button
              onClick={deleteExperiment}
              className="text-xs px-3 py-1.5 rounded border transition-colors hover:bg-red-50"
              style={{ borderColor: '#fecaca', color: '#dc2626' }}
            >
              删除
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="p-6 max-w-4xl">
          {/* Title & Status */}
          <div className="mb-6">
            <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
              {experiment.title}
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              创建于 {new Date(experiment.created_at).toLocaleString()}
            </p>
          </div>

          {/* Status Actions */}
          <div
            className="flex flex-wrap gap-2 mb-6 p-3 rounded-lg border"
            style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
          >
            {experiment.status !== 'pending' && (
              <button
                onClick={() => updateStatus('pending')}
                className="px-3 py-1.5 text-xs rounded border transition-colors"
                style={{ backgroundColor: 'white', borderColor: 'var(--border)' }}
              >
                标记为待开始
              </button>
            )}
            {experiment.status !== 'in_progress' && (
              <button
                onClick={() => updateStatus('in_progress')}
                className="px-3 py-1.5 text-xs rounded transition-colors"
                style={{ backgroundColor: '#dbeafe', color: '#2563eb' }}
              >
                标记为进行中
              </button>
            )}
            {experiment.status !== 'completed' && (
              <button
                onClick={() => updateStatus('completed')}
                className="px-3 py-1.5 text-xs rounded transition-colors"
                style={{ backgroundColor: '#dcfce7', color: '#16a34a' }}
              >
                标记为已完成
              </button>
            )}
          </div>

          {/* Description */}
          {experiment.description && (
            <div
              className="mb-6 p-4 rounded-lg border"
              style={{ backgroundColor: 'white', borderColor: 'var(--border)' }}
            >
              <h2 className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>实验描述</h2>
              <div className="text-sm markdown-content" style={{ color: 'var(--text-secondary)' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{experiment.description}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Linked Idea Product Concept */}
          {idea && (
            <div className="mb-6 rounded-xl border overflow-hidden"
              style={{ borderColor: 'var(--border)' }}>
              <div className="px-4 py-3 border-b flex items-center justify-between"
                style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>
                <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  🚀 产品思路参考
                </span>
                {idea.source_url && (
                  <a href={idea.source_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs" style={{ color: 'var(--accent-blue)' }}>
                    📰 {idea.source_title || '查看来源文章'} →
                  </a>
                )}
              </div>
              <div className="p-4 space-y-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
                {idea.inspiration && (
                  <div className="p-3 rounded-lg border-l-2"
                    style={{ backgroundColor: '#fefce8', borderLeftColor: '#fbbf24', color: '#92400e' }}>
                    <span className="font-semibold">✨ 灵感来源: </span>{idea.inspiration}
                  </div>
                )}
                {idea.product_concept?.core_features?.length > 0 && (
                  <div>
                    <div className="font-semibold mb-1" style={{ color: 'var(--text-muted)' }}>⚙️ 核心功能</div>
                    <ul className="space-y-1">
                      {idea.product_concept.core_features.map((f, i) => (
                        <li key={i} className="flex items-start gap-1">
                          <span style={{ color: 'var(--accent-blue)' }}>▸</span>{f}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {idea.product_concept?.roadmap?.length > 0 && (
                  <div>
                    <div className="font-semibold mb-2" style={{ color: 'var(--text-muted)' }}>🗺️ 实施路径</div>
                    <div className="flex flex-wrap gap-1 items-center">
                      {idea.product_concept.roadmap.map((step, i) => (
                        <span key={i} className="flex items-center gap-1">
                          <span className="w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: 'var(--accent-blue)', color: 'white' }}>{i + 1}</span>
                          <span>{step}</span>
                          {i < idea.product_concept.roadmap.length - 1 && (
                            <span style={{ color: 'var(--text-muted)' }}>→</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {idea.source_context && (
                  <div className="p-2 rounded" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                    <span className="font-medium">文章摘要: </span>
                    {idea.source_context.slice(0, 300)}{idea.source_context.length > 300 ? '...' : ''}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Product Concept */}
          <div
            className="mb-6 rounded-xl border overflow-hidden"
            style={{ borderColor: productConcept ? '#c4b5fd' : 'var(--border)' }}
          >
            <div className="px-4 py-3 border-b flex items-center justify-between"
              style={{ backgroundColor: productConcept ? '#faf5ff' : 'var(--bg-secondary)', borderColor: productConcept ? '#e9d5ff' : 'var(--border)' }}>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>💡 产品思路</span>
                {productConcept?.generated_at && (
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    生成于 {new Date(productConcept.generated_at).toLocaleString()}
                  </span>
                )}
              </div>
              <button
                onClick={generateIdeas}
                disabled={generating}
                className="px-3 py-1.5 text-xs rounded font-medium transition-colors disabled:opacity-50"
                style={{ backgroundColor: generating ? 'var(--border)' : 'var(--accent-blue)', color: 'white' }}
              >
                {generating ? '生成中...' : productConcept ? '重新生成' : '生成产品思路'}
              </button>
            </div>

            {generating && !productConcept && (
              <div className="flex items-center gap-2 py-8 justify-center text-sm" style={{ color: 'var(--text-muted)' }}>
                <span className="loading-pulse">▌</span>
                <span>AI 正在生成产品思路，约需 20-40 秒...</span>
              </div>
            )}

            {productConcept?.content ? (
              <div style={{ backgroundColor: 'white' }}>
                <div className="p-5 markdown-content text-sm" style={{ lineHeight: 1.8 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{productConcept.content}</ReactMarkdown>
                </div>
                <div className="px-5 pb-5 pt-2 border-t flex items-center justify-between"
                  style={{ borderColor: '#e9d5ff' }}>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    复制为 Vibe Coding 启动 Prompt，粘贴到 Claude Code / Cursor 开始实现
                  </span>
                  <button
                    onClick={copyVibeCodingPrompt}
                    className="px-4 py-2 text-xs rounded-lg font-medium transition-all"
                    style={{
                      backgroundColor: copied ? '#dcfce7' : '#f3e8ff',
                      color: copied ? '#16a34a' : '#7c3aed',
                      border: `1px solid ${copied ? '#86efac' : '#c4b5fd'}`
                    }}
                  >
                    {copied ? '✓ 已复制！' : '⚡ 复制启动 Prompt'}
                  </button>
                </div>
              </div>
            ) : !generating ? (
              <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                点击"生成产品思路"，AI 将为你生成完整的产品方案和 Vibe Coding 启动提示词
              </div>
            ) : null}
          </div>

          {/* Logs */}
          <div
            className="mb-6 p-4 rounded-lg border"
            style={{ backgroundColor: 'white', borderColor: 'var(--border)' }}
          >
            <h2 className="font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
              📝 实验日志 ({logs.length})
            </h2>

            {/* Add Log */}
            <form onSubmit={addLog} className="mb-4">
              <textarea
                placeholder="记录新的进展..."
                value={newLog}
                onChange={e => setNewLog(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded border focus:outline-none focus:ring-2"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'var(--bg-primary)'
                }}
                rows="3"
              />
              <button
                type="submit"
                className="mt-2 px-4 py-2 text-xs rounded font-medium"
                style={{ backgroundColor: 'var(--accent-blue)', color: 'white' }}
              >
                添加日志
              </button>
            </form>

            {/* Logs List */}
            <div className="space-y-3">
              {logs.length === 0 ? (
                <p className="text-sm text-center py-4" style={{ color: 'var(--text-muted)' }}>暂无日志</p>
              ) : (
                logs.map(log => (
                  <div
                    key={log.id}
                    className="p-3 rounded border"
                    style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-light)' }}
                  >
                    <p className="text-sm whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                      {log.content}
                    </p>
                    <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
                      {new Date(log.created_at).toLocaleString()}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
    </>
  )
}

export default ExperimentDetail
