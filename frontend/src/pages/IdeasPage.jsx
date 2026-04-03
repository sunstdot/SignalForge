import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

const FILTER_TABS = [
  { key: 'pending', label: '待选' },
  { key: 'selected', label: '已选' },
  { key: 'in-progress', label: '进行中' },
  { key: 'completed', label: '已完成' },
  { key: 'all', label: '全部' }
]

const DIFFICULTY_MAP = {
  easy: { label: '简单', badge: 'badge-easy' },
  medium: { label: '中等', badge: 'badge-medium' },
  hard: { label: '困难', badge: 'badge-hard' }
}

const STATUS_MAP = {
  pending: { label: '待选', badge: 'badge-pending' },
  selected: { label: '已选', badge: 'badge-selected' },
  'in-progress': { label: '进行中', badge: 'badge-in-progress' },
  completed: { label: '已完成', badge: 'badge-completed' },
  archived: { label: '已归档', badge: 'badge-pending' }
}

function IdeasPage() {
  const [ideas, setIdeas] = useState([])
  const [stats, setStats] = useState({ total: 0, pending: 0, selected: 0, 'in-progress': 0, completed: 0 })
  const [activeFilter, setActiveFilter] = useState('pending')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [activeFilter])

  async function fetchData() {
    setLoading(true)
    try {
      const [ideasRes, statsRes] = await Promise.all([
        fetch(`/api/experiments/ideas${activeFilter !== 'all' ? `?status=${activeFilter}` : ''}`),
        fetch('/api/experiments/ideas/stats')
      ])
      
      const ideasData = await ideasRes.json()
      const statsData = await statsRes.json()
      
      setIdeas(ideasData.ideas || [])
      setStats(statsData)
    } catch (error) {
      console.error('Failed to fetch ideas:', error)
    } finally {
      setLoading(false)
    }
  }

  async function updateStatus(ideaId, newStatus) {
    try {
      await fetch(`/api/experiments/ideas/${ideaId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      })
      fetchData()
    } catch (error) {
      console.error('Failed to update status:', error)
    }
  }

  async function deleteIdea(ideaId) {
    if (!confirm('确定要删除这个想法吗？')) return
    try {
      await fetch(`/api/experiments/ideas/${ideaId}`, { method: 'DELETE' })
      fetchData()
    } catch (error) {
      console.error('Failed to delete idea:', error)
    }
  }

  async function createExperiment(idea) {
    try {
      const res = await fetch('/api/experiments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: idea.title,
          description: idea.description,
          idea_id: idea.id,
          target_days: idea.estimated_days,
          status: 'planning'
        })
      })
      const data = await res.json()
      // 更新想法状态为 selected
      await updateStatus(idea.id, 'selected')
      alert('实验已创建！')
    } catch (error) {
      console.error('Failed to create experiment:', error)
    }
  }

  const filteredIdeas = activeFilter === 'all' 
    ? ideas 
    : ideas.filter(i => i.status === activeFilter)

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
        <div className="p-5">
          <h1 className="text-xl font-bold mb-1" style={{ color: 'var(--text-primary)' }}>TokenBurner</h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>AI Intelligence Hub</p>
        </div>

        {/* Menu */}
        <div className="px-3 pb-3">
          <div 
            className="text-xs font-semibold uppercase tracking-wider mb-2 px-3"
            style={{ color: 'var(--text-muted)' }}
          >
            Menu
          </div>
          <Link to="/" className="menu-item">
            <span>📊</span>
            <span>情报总览</span>
          </Link>
          <Link to="/experiments/live" className="menu-item">
            <span>🔬</span>
            <span>实验直播场</span>
          </Link>
          <Link to="/experiments/ideas" className="menu-item active">
            <span>💡</span>
            <span>实验想法池</span>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64">
        {/* Header */}
        <header 
          className="sticky top-0 z-20 px-6 py-4 border-b"
          style={{ 
            backgroundColor: 'var(--bg-primary)',
            borderColor: 'var(--border)'
          }}
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="window-dots">
              <span className="window-dot window-dot-red" />
              <span className="window-dot window-dot-yellow" />
              <span className="window-dot window-dot-green" />
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Link to="/" style={{ color: 'var(--text-primary)' }}>TokenBurner</Link>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span style={{ color: 'var(--accent-blue)' }}>实验想法池</span>
            </div>
          </div>
          
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            从日报中发现的实践机会
          </p>
        </header>

        <div className="p-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="stat-card">
              <div className="stat-number" style={{ color: 'var(--accent-blue)' }}>{stats.total}</div>
              <div className="stat-label">当前显示</div>
            </div>
            <div className="stat-card">
              <div className="stat-number" style={{ color: 'var(--accent-yellow)' }}>{stats.pending}</div>
              <div className="stat-label">待选</div>
            </div>
            <div className="stat-card">
              <div className="stat-number" style={{ color: 'var(--accent-blue)' }}>{stats.selected}</div>
              <div className="stat-label">已选</div>
            </div>
            <div className="stat-card">
              <div className="stat-number" style={{ color: 'var(--accent-green)' }}>{stats.completed}</div>
              <div className="stat-label">已完成</div>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-2 mb-6">
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>状态筛选:</span>
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveFilter(tab.key)}
                className={`filter-tab ${activeFilter === tab.key ? 'active' : ''}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Ideas List */}
          {loading ? (
            <div className="text-center py-12">
              <span className="loading-pulse">▌</span>
              <span className="text-sm ml-2" style={{ color: 'var(--text-muted)' }}>加载中...</span>
            </div>
          ) : filteredIdeas.length === 0 ? (
            <div className="text-center py-12">
              <span className="text-3xl block mb-2">∅</span>
              <p style={{ color: 'var(--text-muted)' }}>暂无想法</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredIdeas.map((idea) => (
                <IdeaCard 
                  key={idea.id} 
                  idea={idea} 
                  onUpdateStatus={updateStatus}
                  onDelete={deleteIdea}
                  onCreateExp={createExperiment}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function IdeaCard({ idea, onUpdateStatus, onDelete, onCreateExp }) {
  const diffInfo = DIFFICULTY_MAP[idea.difficulty] || DIFFICULTY_MAP.medium
  const statusInfo = STATUS_MAP[idea.status] || STATUS_MAP.pending

  // 渲染星级
  const stars = Math.round((idea.priority || 0) / 2)

  return (
    <div className="idea-card">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`badge ${diffInfo.badge}`}>{diffInfo.label}</span>
          <h3 className="font-semibold text-lg" style={{ color: 'var(--text-primary)' }}>
            {idea.title}
          </h3>
          <span className={`badge ${statusInfo.badge}`}>{statusInfo.label}</span>
        </div>
        <div className="flex items-center gap-2">
          {idea.status === 'pending' && (
            <button
              onClick={() => onCreateExp(idea)}
              className="btn-primary text-sm"
            >
              选择这个想法
            </button>
          )}
          <button
            onClick={() => onDelete(idea.id)}
            className="btn-danger text-sm"
          >
            删除
          </button>
        </div>
      </div>

      {/* Description */}
      <div className="markdown-content text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
        <ReactMarkdown>{idea.description}</ReactMarkdown>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: 'var(--border-light)' }}>
        <div className="flex flex-wrap gap-2">
          {(idea.tags || []).map((tag) => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            预计 {idea.estimated_days} 天
          </span>
          <span className="text-yellow-500">
            {'★'.repeat(stars)}{'☆'.repeat(5 - stars)}
          </span>
        </div>
      </div>

      {/* Source */}
      {idea.source_title && (
        <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--border-light)' }}>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            来源: {idea.source_title}
          </p>
        </div>
      )}
    </div>
  )
}

export default IdeasPage
