import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

function ExperimentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [experiment, setExperiment] = useState(null)
  const [logs, setLogs] = useState([])
  const [ideas, setIdeas] = useState('')
  const [newLog, setNewLog] = useState('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

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

  const generateIdeas = () => {
    setGenerating(true)
    fetch(`/api/experiments/${id}/ideas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: experiment?.description || '' })
    })
      .then(res => res.json())
      .then(data => {
        setIdeas(data.ideas)
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
    <div className="min-h-screen flex">
      {/* Left Sidebar */}
      <aside 
        className="w-64 flex-shrink-0 fixed left-0 top-0 bottom-0 overflow-y-auto"
        style={{ 
          borderRight: '1px solid var(--border)',
          backgroundColor: 'var(--bg-secondary)'
        }}
      >
        {/* Header */}
        <div 
          className="p-4 border-b"
          style={{ 
            borderColor: 'var(--border)',
            backgroundColor: 'var(--bg-primary)'
          }}
        >
          <Link to="/" className="flex items-center gap-2 mb-3">
            <span style={{ color: 'var(--accent-blue)' }}>◈</span>
            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>TokenBurner</span>
          </Link>
          <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Experiments Lab
          </div>
        </div>

        {/* Navigation */}
        <div className="p-3">
          <div 
            className="text-xs font-medium uppercase tracking-wider mb-2 px-2"
            style={{ color: 'var(--text-muted)' }}
          >
            Navigation
          </div>
          <nav className="space-y-1">
            <Link to="/experiments" className="date-nav-item">
              <span>←</span>
              <span>返回列表</span>
            </Link>
          </nav>
        </div>

        {/* Info Panel */}
        <div className="p-3">
          <div 
            className="text-xs font-medium uppercase tracking-wider mb-2 px-2"
            style={{ color: 'var(--text-muted)' }}
          >
            Info
          </div>
          <div 
            className="p-3 rounded-lg border"
            style={{ 
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border)'
            }}
          >
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-muted)' }}>ID:</span>
                <span style={{ color: 'var(--text-secondary)' }}>{experiment.id.slice(0, 8)}...</span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-muted)' }}>Status:</span>
                <span 
                  className="px-1.5 py-0.5 rounded text-[10px]"
                  style={{ backgroundColor: statusStyle.bg, color: statusStyle.text }}
                >
                  {getStatusText(experiment.status)}
                </span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-muted)' }}>Created:</span>
                <span style={{ color: 'var(--text-secondary)' }}>
                  {new Date(experiment.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-muted)' }}>Logs:</span>
                <span style={{ color: 'var(--text-secondary)' }}>{logs.length}</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64">
        {/* Top Bar */}
        <header 
          className="sticky top-0 z-20 border-b px-4 py-3"
          style={{ 
            backgroundColor: 'var(--bg-primary)',
            borderColor: 'var(--border)'
          }}
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
                <Link to="/experiments" style={{ color: 'var(--text-muted)' }}>Experiments</Link>
                <span style={{ color: 'var(--text-muted)' }}>/</span>
                <span style={{ color: 'var(--accent-blue)' }} className="font-medium">
                  {experiment.title}
                </span>
              </div>
            </div>
            <button
              onClick={deleteExperiment}
              className="text-xs px-3 py-1.5 rounded border transition-colors hover:bg-red-50"
              style={{ borderColor: '#fecaca', color: '#dc2626' }}
            >
              删除
            </button>
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
              <p className="text-sm whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                {experiment.description}
              </p>
            </div>
          )}

          {/* AI Ideas */}
          <div 
            className="mb-6 p-4 rounded-lg border"
            style={{ backgroundColor: 'white', borderColor: 'var(--border)' }}
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>💡 AI 实验想法</h2>
              <button
                onClick={generateIdeas}
                disabled={generating}
                className="px-3 py-1.5 text-xs rounded font-medium transition-colors disabled:opacity-50"
                style={{ backgroundColor: 'var(--accent-blue)', color: 'white' }}
              >
                {generating ? '生成中...' : '生成想法'}
              </button>
            </div>
            
            {ideas && (
              <div 
                className="p-3 rounded text-sm prose prose-sm max-w-none"
                style={{ backgroundColor: 'var(--bg-secondary)' }}
              >
                <ReactMarkdown>{ideas}</ReactMarkdown>
              </div>
            )}
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
      </main>
    </div>
  )
}

export default ExperimentDetail
