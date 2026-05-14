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

  useEffect(() => { fetchData() }, [activeFilter])

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
      await fetch('/api/experiments', {
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
      await updateStatus(idea.id, 'selected')
      alert('实验已创建！')
    } catch (error) {
      console.error('Failed to create experiment:', error)
    }
  }

  const filteredIdeas = activeFilter === 'all' ? ideas : ideas.filter(i => i.status === activeFilter)

  return (
    <>
      <header className="sticky top-0 z-20 px-6 py-4 border-b"
        style={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)' }}>
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
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>从日报中发现的实践机会</p>
      </header>

      <div className="p-6">
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

        <div className="flex items-center gap-2 mb-6">
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>状态筛选:</span>
          {FILTER_TABS.map((tab) => (
            <button key={tab.key} onClick={() => setActiveFilter(tab.key)}
              className={`filter-tab ${activeFilter === tab.key ? 'active' : ''}`}>
              {tab.label}
            </button>
          ))}
        </div>

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
              <IdeaCard key={idea.id} idea={idea}
                onUpdateStatus={updateStatus}
                onDelete={deleteIdea}
                onCreateExp={createExperiment} />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

function IdeaCard({ idea, onUpdateStatus, onDelete, onCreateExp }) {
  const diffInfo = DIFFICULTY_MAP[idea.difficulty] || DIFFICULTY_MAP.medium
  const statusInfo = STATUS_MAP[idea.status] || STATUS_MAP.pending
  const stars = Math.min(5, Math.max(0, Math.round((idea.priority || 0) / 2)))
  const [showConcept, setShowConcept] = useState(false)
  const concept = idea.product_concept || {}

  return (
    <div className="idea-card">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`badge ${diffInfo.badge}`}>{diffInfo.label}</span>
          <h3 className="font-semibold text-lg" style={{ color: 'var(--text-primary)' }}>{idea.title}</h3>
          <span className={`badge ${statusInfo.badge}`}>{statusInfo.label}</span>
        </div>
        <div className="flex items-center gap-2">
          {idea.status === 'pending' && (
            <button onClick={() => onCreateExp(idea)} className="btn-primary text-sm">选择这个想法</button>
          )}
          <button onClick={() => onDelete(idea.id)} className="btn-danger text-sm">删除</button>
        </div>
      </div>

      {/* Inspiration banner (if product concept) */}
      {idea.inspiration && (
        <div className="mb-3 p-3 rounded-lg border-l-2 text-xs"
          style={{ backgroundColor: '#fefce8', borderLeftColor: '#fbbf24', color: '#92400e' }}>
          <span className="font-semibold">✨ 灵感来源：</span>{idea.inspiration}
        </div>
      )}

      {/* Description */}
      <div className="markdown-content text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
        <ReactMarkdown>{idea.description}</ReactMarkdown>
      </div>

      {/* Expand full product concept if available */}
      {concept.product_definition && (
        <div className="mb-4">
          <button
            onClick={() => setShowConcept(v => !v)}
            className="text-xs flex items-center gap-1"
            style={{ color: 'var(--accent-blue)' }}>
            <span>{showConcept ? '▲' : '▶'}</span>
            <span>{showConcept ? '收起产品思路' : '查看完整产品思路'}</span>
          </button>

          {showConcept && (
            <div className="mt-3 space-y-3 text-xs p-3 rounded-lg border"
              style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
              {concept.core_features && concept.core_features.length > 0 && (
                <div>
                  <div className="font-semibold mb-1" style={{ color: 'var(--text-muted)' }}>⚙️ 核心功能</div>
                  <ul className="space-y-1">
                    {concept.core_features.map((f, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span style={{ color: 'var(--accent-blue)' }}>▸</span>{f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {concept.target_users && (
                <div><span className="font-semibold" style={{ color: 'var(--text-muted)' }}>👤 目标用户: </span>{concept.target_users}</div>
              )}
              {concept.business_value && (
                <div><span className="font-semibold" style={{ color: 'var(--text-muted)' }}>💰 商业价值: </span>{concept.business_value}</div>
              )}
              {concept.roadmap && concept.roadmap.length > 0 && (
                <div>
                  <div className="font-semibold mb-1" style={{ color: 'var(--text-muted)' }}>🗺️ 实施路径</div>
                  <div className="flex flex-wrap gap-1 items-center">
                    {concept.roadmap.map((step, i) => (
                      <span key={i} className="flex items-center gap-1">
                        <span className="w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: 'var(--accent-blue)', color: 'white' }}>{i + 1}</span>
                        <span>{step}</span>
                        {i < concept.roadmap.length - 1 && <span style={{ color: 'var(--text-muted)' }}>→</span>}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: 'var(--border-light)' }}>
        <div className="flex flex-wrap gap-2">
          {(idea.tags || []).map((tag) => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>预计 {idea.estimated_days} 天</span>
          <span className="text-yellow-500">{'★'.repeat(stars)}{'☆'.repeat(5 - stars)}</span>
        </div>
      </div>

      {/* Source */}
      {idea.source_title && (
        <div className="mt-3 pt-3 border-t flex items-start gap-1" style={{ borderColor: 'var(--border-light)' }}>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>📰 基于:</span>
          {idea.source_url ? (
            <a href={idea.source_url} target="_blank" rel="noopener noreferrer"
              className="text-xs flex-1" style={{ color: 'var(--accent-blue)' }}>
              {idea.source_title}
            </a>
          ) : (
            <span className="text-xs flex-1" style={{ color: 'var(--text-muted)' }}>{idea.source_title}</span>
          )}
        </div>
      )}

      {/* Source context excerpt */}
      {idea.source_context && (
        <div className="mt-2 text-xs px-2 py-2 rounded" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
          <span className="font-medium">文章摘要: </span>
          {idea.source_context.slice(0, 200)}{idea.source_context.length > 200 ? '...' : ''}
        </div>
      )}
    </div>
  )
}

export default IdeasPage
