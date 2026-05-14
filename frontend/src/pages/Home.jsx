import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function Home() {
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/dates')
      .then(res => res.json())
      .then(data => {
        const latest = data.dates?.[0]
        if (latest) {
          navigate(`/briefing/${latest}`, { replace: true })
        }
      })
      .catch(() => {})
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
        <span className="loading-pulse">▌</span>
        <span className="text-sm">加载中...</span>
      </div>
    </div>
  )
}

export default Home
