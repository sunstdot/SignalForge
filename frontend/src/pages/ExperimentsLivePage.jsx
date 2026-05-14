import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const STATUS_MAP = {
  planning: { label: '规划中', color: '#6b7280' },
  'in-progress': { label: '进行中', color: '#ca8a04' },
  completed: { label: '已完成', color: '#16a34a' },
  archived: { label: '已归档', color: '#9ca3af' }
}

function ExperimentsLivePage() {
  const [experiments, setExperiments] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchExperiments()
  }, [])

  async function fetchExperiments() {
    setLoading(true)
    try {
      const res = await fetch('/api/experiments')
      const data = await res.json()
      setExperiments(data.experiments || [])
    } catch (error) {
      console.error('Failed to fetch experiments:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <header
        className="sticky top-0 z-20 px-6 py-4 border-b"
        style={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)' }}
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
            <span style={{ color: 'var(--accent-blue)' }}>实验直播场</span>
          </div>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>正在进行的实验项目</p>
      </header>

      <div className="p-6">
        {loading ? (
          <div className="text-center py-12">
            <span className="loading-pulse">▌</span>
            <span className="text-sm ml-2" style={{ color: 'var(--text-muted)' }}>加载中...</span>
          </div>
        ) : experiments.length === 0 ? (
          <div className="text-center py-12">
            <span className="text-3xl block mb-2">∅</span>
            <p style={{ color: 'var(--text-muted)' }}>暂无实验</p>
            <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>
              从<a href="/experiments/ideas" style={{ color: 'var(--accent-blue)' }}>实验想法池</a>选择一个想法开始
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {experiments.map((exp) => (
              <ExperimentCard key={exp.id} experiment={exp} />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

function ExperimentCard({ experiment }) {
  const statusInfo = STATUS_MAP[experiment.status] || STATUS_MAP.planning

  return (
    <Link 
      to={`/experiments/${experiment.id}`}
      className="block p-5 rounded-xl border transition-all hover:shadow-md"
      style={{ 
        backgroundColor: 'white',
        borderColor: 'var(--border)'
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-lg" style={{ color: 'var(--text-primary)' }}>
          {experiment.title}
        </h3>
        <span 
          className="text-xs px-2 py-1 rounded-full"
          style={{ backgroundColor: statusInfo.color + '20', color: statusInfo.color }}
        >
          {statusInfo.label}
        </span>
      </div>
      
      <p className="text-sm line-clamp-2 mb-4" style={{ color: 'var(--text-secondary)' }}>
        {experiment.description || '暂无描述'}
      </p>

      <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--text-muted)' }}>
        <span>目标: {experiment.target_days} 天</span>
        <span>创建于 {new Date(experiment.created_at).toLocaleDateString()}</span>
      </div>
    </Link>
  )
}

export default ExperimentsLivePage
