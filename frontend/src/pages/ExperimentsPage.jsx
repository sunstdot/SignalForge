import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

function ExperimentsPage() {
  const [experiments, setExperiments] = useState([])
  const [newExperiment, setNewExperiment] = useState({ title: '', description: '' })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchExperiments()
  }, [])

  const fetchExperiments = () => {
    setLoading(true)
    fetch('/api/experiments')
      .then(res => res.json())
      .then(data => {
        setExperiments(data.experiments || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  const createExperiment = (e) => {
    e.preventDefault()
    fetch('/api/experiments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newExperiment)
    })
      .then(res => res.json())
      .then(data => {
        setNewExperiment({ title: '', description: '' })
        window.location.href = `/experiments/${data.id}`
      })
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return { bg: '#dcfce7', text: '#16a34a' }
      case 'in_progress': return { bg: '#dbeafe', text: '#2563eb' }
      case 'pending': return { bg: '#f3f4f6', text: '#6b7280' }
      default: return { bg: '#f3f4f6', text: '#6b7280' }
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
            Menu
          </div>
          <nav className="space-y-1">
            <Link to="/" className="date-nav-item">
              <span>←</span>
              <span>返回简报</span>
            </Link>
          </nav>
        </div>

        {/* Footer */}
        <div 
          className="absolute bottom-0 left-0 right-0 p-4 border-t"
          style={{ 
            borderColor: 'var(--border)',
            backgroundColor: 'var(--bg-secondary)'
          }}
        >
          <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--accent-blue)' }} />
              {experiments.length} experiments
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
          <div className="flex items-center gap-4">
            <div className="window-dots">
              <span className="window-dot window-dot-red" />
              <span className="window-dot window-dot-yellow" />
              <span className="window-dot window-dot-green" />
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Link to="/" style={{ color: 'var(--text-muted)' }}>TokenBurner</Link>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span style={{ color: 'var(--accent-blue)' }} className="font-medium">Experiments</span>
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="p-6 max-w-5xl">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Experiments List */}
            <div className="lg:col-span-2">
              <div 
                className="flex justify-between items-center mb-4 pb-2 border-b"
                style={{ borderColor: 'var(--border)' }}
              >
                <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>实验列表</h2>
                <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                  {experiments.length} 个实验
                </span>
              </div>
              
              {experiments.length === 0 ? (
                <div 
                  className="text-center py-12 rounded-lg border"
                  style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
                >
                  <span className="text-3xl block mb-2">∅</span>
                  <p className="text-sm" style={{ color: 'var(--text-muted)' }}>暂无实验</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {experiments.map(exp => {
                    const statusStyle = getStatusColor(exp.status)
                    return (
                      <Link
                        key={exp.id}
                        to={`/experiments/${exp.id}`}
                        className="block p-4 rounded-lg border transition-all hover:shadow-sm"
                        style={{ 
                          backgroundColor: 'white',
                          borderColor: 'var(--border)'
                        }}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h3 className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                              {exp.title}
                            </h3>
                            <p className="text-sm line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                              {exp.description || '暂无描述'}
                            </p>
                            <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
                              创建于 {new Date(exp.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <span 
                            className="text-xs px-2 py-1 rounded-full ml-4"
                            style={{ backgroundColor: statusStyle.bg, color: statusStyle.text }}
                          >
                            {getStatusText(exp.status)}
                          </span>
                        </div>
                      </Link>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Create New Experiment */}
            <div className="lg:col-span-1">
              <div 
                className="p-5 rounded-lg border sticky top-24"
                style={{ 
                  backgroundColor: 'white',
                  borderColor: 'var(--border)'
                }}
              >
                <h3 className="font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>新建实验</h3>
                <form onSubmit={createExperiment} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                      实验标题
                    </label>
                    <input
                      type="text"
                      placeholder="输入实验标题..."
                      value={newExperiment.title}
                      onChange={e => setNewExperiment({...newExperiment, title: e.target.value})}
                      className="w-full px-3 py-2 text-sm rounded border focus:outline-none focus:ring-2"
                      style={{ 
                        borderColor: 'var(--border)',
                        backgroundColor: 'var(--bg-primary)'
                      }}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                      实验描述
                    </label>
                    <textarea
                      placeholder="描述你的实验..."
                      value={newExperiment.description}
                      onChange={e => setNewExperiment({...newExperiment, description: e.target.value})}
                      className="w-full px-3 py-2 text-sm rounded border focus:outline-none focus:ring-2"
                      style={{ 
                        borderColor: 'var(--border)',
                        backgroundColor: 'var(--bg-primary)'
                      }}
                      rows="4"
                    />
                  </div>
                  <button 
                    type="submit"
                    className="w-full px-4 py-2 text-sm rounded font-medium transition-colors"
                    style={{ 
                      backgroundColor: 'var(--accent-blue)',
                      color: 'white'
                    }}
                  >
                    创建实验
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default ExperimentsPage
