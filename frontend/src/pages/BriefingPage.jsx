import { useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

const CATEGORY_TABS = [
  { key: 'all', label: '全部', icon: '∗' },
  { key: 'paper', label: '论文', icon: '📄' },
  { key: 'repo', label: '仓库', icon: '🛠️' },
  { key: 'model', label: '模型', icon: '🤖' },
  { key: 'news', label: '资讯', icon: '📰' }
]

const SOURCE_TYPE_MAP = {
  arxiv: { label: '论文', badge: 'badge-paper' },
  paper: { label: '论文', badge: 'badge-paper' },
  repo: { label: '仓库', badge: 'badge-repo' },
  github: { label: '仓库', badge: 'badge-repo' },
  model: { label: '模型', badge: 'badge-model' },
  rss: { label: '资讯', badge: 'badge-news' },
  smolai: { label: '资讯', badge: 'badge-news' },
  newsletter: { label: '资讯', badge: 'badge-news' },
  tweet: { label: '动态', badge: 'badge-news' },
  podcast: { label: '播客', badge: 'badge-news' },
  news: { label: '资讯', badge: 'badge-news' }
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return days[date.getDay()]
}

function BriefingPage() {
  const { date } = useParams()
  const [briefing, setBriefing] = useState(null)
  const [dates, setDates] = useState([])
  const [activeCategory, setActiveCategory] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [date])

  async function fetchData() {
    setLoading(true)
    try {
      const [briefingRes, datesRes] = await Promise.all([
        fetch(`/api/briefing/${date}`),
        fetch('/api/dates')
      ])
      
      const briefingData = await briefingRes.json()
      const datesData = await datesRes.json()
      
      setBriefing(briefingData)
      setDates(datesData.dates.map((d) => ({
        date: d,
        formattedDate: formatDate(d)
      })))
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredItems = useMemo(() => {
    if (!briefing) return []
    const items = briefing.items || []
    if (activeCategory === 'all') return items
    return items.filter(item => {
      const type = item.source_type
      if (activeCategory === 'paper') return type === 'arxiv' || type === 'paper'
      if (activeCategory === 'repo') return type === 'repo' || type === 'github'
      if (activeCategory === 'model') return type === 'model'
      if (activeCategory === 'news') return ['rss', 'smolai', 'newsletter', 'tweet', 'podcast', 'news'].includes(type)
      return true
    })
  }, [briefing, activeCategory])

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

  if (!briefing) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <div className="window-dots justify-center mb-4">
            <span className="window-dot window-dot-red" />
            <span className="window-dot window-dot-yellow" />
            <span className="window-dot window-dot-green" />
          </div>
          <h2 className="text-lg font-semibold mb-2">简报未找到</h2>
          <Link to="/" style={{ color: 'var(--accent-blue)' }} className="text-sm">
            返回首页
          </Link>
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
          <Link to="/experiments/ideas" className="menu-item">
            <span>💡</span>
            <span>实验想法池</span>
          </Link>
        </div>
        
        {/* Archives */}
        <div className="px-3 py-3">
          <div 
            className="text-xs font-semibold uppercase tracking-wider mb-2 px-3"
            style={{ color: 'var(--text-muted)' }}
          >
            Archives
          </div>
          <nav className="space-y-1">
            {dates.map((d) => (
              <Link
                key={d.date}
                to={`/briefing/${d.date}`}
                className={`date-nav-item ${d.date === date ? 'active' : ''}`}
              >
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{d.formattedDate}</span>
                <span className="font-mono">{d.date}</span>
              </Link>
            ))}
          </nav>
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
              <span style={{ color: 'var(--text-primary)' }}>TokenBurner</span>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span style={{ color: 'var(--accent-blue)' }}>{date}</span>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span style={{ color: 'var(--text-primary)' }}>AI技术日报</span>
            </div>
          </div>
        </header>

        {/* Category Tabs */}
        <div 
          className="px-6 py-4 border-b"
          style={{ borderColor: 'var(--border)' }}
        >
          <div className="flex gap-2">
            {CATEGORY_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveCategory(tab.key)}
                className={`tab-btn ${activeCategory === tab.key ? 'active' : ''}`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6" style={{ maxWidth: '900px' }}>
          {/* Summary */}
          {briefing.summary && (
            <div className="mb-6">
              <h2 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>
                AI 技术日报总览
              </h2>
              <div className="markdown-content text-sm" style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                <ReactMarkdown>{briefing.summary}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Items */}
          <section className="space-y-4">
            {filteredItems.map((item, index) => (
              <ContentCard key={item.id} item={item} index={index + 1} />
            ))}
          </section>
        </div>
      </main>
    </div>
  )
}

function ContentCard({ item, index }) {
  const typeInfo = SOURCE_TYPE_MAP[item.source_type] || { label: '资讯', badge: 'badge-news' }

  return (
    <article className="content-card">
      <div className="card-header">
        <span className="text-sm" style={{ color: 'var(--text-muted)' }}>#{index}</span>
        <span className={`badge ${typeInfo.badge}`}>{typeInfo.label}</span>
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          来源: {item.source}
        </span>
        <span className="text-sm ml-auto" style={{ color: 'var(--text-muted)' }}>
          相关度: {item.relevance_score}/10
        </span>
      </div>
      
      <div className="p-5">
        {/* Title */}
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
          {item.title}
        </h3>

        {/* Summary */}
        {item.summary && (
          <div className="markdown-content text-sm mb-4">
            <ReactMarkdown>{item.summary}</ReactMarkdown>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: 'var(--border-light)' }}>
          <div className="flex flex-wrap gap-2">
            {(item.category || []).slice(0, 4).map((cat) => (
              <span key={cat} className="tag">{cat}</span>
            ))}
          </div>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm flex items-center gap-1"
            style={{ color: 'var(--accent-blue)' }}
          >
            阅读原文 →
          </a>
        </div>
      </div>
    </article>
  )
}

export default BriefingPage
