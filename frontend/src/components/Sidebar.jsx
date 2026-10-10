import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

function formatDate(dateStr) {
  const date = new Date(dateStr)
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return days[date.getDay()]
}

function Sidebar() {
  const [dates, setDates] = useState([])
  const [opportunityDates, setOpportunityDates] = useState([])
  const [ventureWeeks, setVentureWeeks] = useState([])
  const location = useLocation()
  // Extract current date from daily content routes if present
  const briefingMatch = location.pathname.match(/^\/briefing\/(.+)$/)
  const opportunityMatch = location.pathname.match(/^\/daily-opportunities\/(.+)$/)
  const ventureWeekMatch = location.pathname.match(/^\/venture-radar\/week\/(.+)$/)
  const currentDate = briefingMatch ? briefingMatch[1] : opportunityMatch ? opportunityMatch[1] : null
  const currentVentureWeek = ventureWeekMatch ? ventureWeekMatch[1] : null
  const latestDate = dates[0]?.date
  const latestOpportunityDate = opportunityDates[0]?.date
  const isDailyOpportunity = Boolean(opportunityMatch)
  const isVentureRadar = location.pathname === '/venture-radar' || location.pathname.startsWith('/venture-radar/')

  useEffect(() => {
    fetch('/api/dates')
      .then(res => res.json())
      .then(data => {
        setDates((data.dates || []).map(d => ({ date: d, formattedDate: formatDate(d) })))
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch('/api/dates/opportunities')
      .then(res => res.json())
      .then(data => {
        setOpportunityDates((data.dates || []).map(d => ({ date: d, formattedDate: formatDate(d) })))
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!isVentureRadar) return undefined
    let ignore = false
    const loadWeeks = () => {
      fetch('/api/venture-radar/weeks')
        .then(res => res.json())
        .then(data => {
          if (!ignore) setVentureWeeks(data.weeks || [])
        })
        .catch(() => {})
    }
    loadWeeks()
    window.addEventListener('venture-radar-weeks-updated', loadWeeks)
    return () => {
      ignore = true
      window.removeEventListener('venture-radar-weeks-updated', loadWeeks)
    }
  }, [isVentureRadar])

  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/')
  const archiveDates = isDailyOpportunity ? opportunityDates : dates
  const archiveItems = isVentureRadar ? ventureWeeks : archiveDates

  return (
    <aside
      className="w-64 flex-shrink-0 fixed left-0 top-0 bottom-0 overflow-y-auto"
      style={{ borderRight: '1px solid var(--border)', backgroundColor: 'var(--bg-secondary)' }}
    >
      {/* Header */}
      <div className="p-5">
        <h1 className="text-xl font-bold mb-1" style={{ color: 'var(--text-primary)' }}>TokenBurner</h1>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>AI Intelligence Hub</p>
      </div>

      {/* Menu */}
      <div className="px-3 pb-3">
        <div className="text-xs font-semibold uppercase tracking-wider mb-2 px-3" style={{ color: 'var(--text-muted)' }}>
          Menu
        </div>
        <Link to={latestDate ? `/briefing/${latestDate}` : '/'} className={`menu-item ${briefingMatch || location.pathname === '/' ? 'active' : ''}`}>
          <span>📊</span><span>今日 AI 情报</span>
        </Link>
        <Link to={latestOpportunityDate ? `/daily-opportunities/${latestOpportunityDate}` : '/'} className={`menu-item ${opportunityMatch ? 'active' : ''}`}>
          <span>🎯</span><span>今日 AI 情报机会</span>
        </Link>
        <Link to={latestDate ? `/opportunities/${latestDate}` : '/'} className={`menu-item ${isActive('/opportunities') ? 'active' : ''}`}>
          <span>🧭</span><span>机会看板</span>
        </Link>
        <Link to="/experiments/live" className={`menu-item ${isActive('/experiments/live') ? 'active' : ''}`}>
          <span>🔬</span><span>实验直播场</span>
        </Link>
        <Link to="/experiments/ideas" className={`menu-item ${isActive('/experiments/ideas') ? 'active' : ''}`}>
          <span>💡</span><span>实验想法池</span>
        </Link>
        <div style={{ height: '1px', background: 'var(--border)', margin: '6px 8px' }} />
        <Link to="/manual-intel" className={`menu-item ${isActive('/manual-intel') ? 'active' : ''}`}>
          <span>📌</span><span>我的情报收藏</span>
        </Link>
        <Link to="/search" className={`menu-item ${isActive('/search') ? 'active' : ''}`}>
          <span>🔍</span><span>情报搜索</span>
        </Link>
        <Link to="/venture-radar" className={`menu-item ${isActive('/venture-radar') ? 'active' : ''}`}>
          <span>🛰️</span><span>创投产品雷达</span>
        </Link>
      </div>

      {/* Archives */}
      {archiveItems.length > 0 && (
        <div className="px-3 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider mb-2 px-3" style={{ color: 'var(--text-muted)' }}>
            Archives
          </div>
          <nav className="space-y-1">
            {isVentureRadar ? ventureWeeks.map(w => (
              <Link
                key={w.week}
                to={`/venture-radar/week/${w.week}`}
                className={`date-nav-item ${w.week === currentVentureWeek ? 'active' : ''}`}
              >
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{w.report_count || 0} reports</span>
                <span className="font-mono">{w.week}</span>
              </Link>
            )) : archiveDates.map(d => (
              <Link
                key={d.date}
                to={opportunityMatch ? `/daily-opportunities/${d.date}` : `/briefing/${d.date}`}
                className={`date-nav-item ${d.date === currentDate ? 'active' : ''}`}
              >
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{d.formattedDate}</span>
                <span className="font-mono">{d.date}</span>
              </Link>
            ))}
          </nav>
        </div>
      )}
    </aside>
  )
}

export default Sidebar
