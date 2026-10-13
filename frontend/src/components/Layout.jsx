import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'

function Layout({ children }) {
  const { pathname } = useLocation()
  const isBriefing = pathname.startsWith('/briefing/')
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => setMenuOpen(false), [pathname])
  useEffect(() => {
    if (!isBriefing || !menuOpen) return undefined
    const closeOnEscape = event => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [isBriefing, menuOpen])

  return (
    <div className={`min-h-screen flex ${isBriefing ? 'briefing-app-layout' : ''} ${menuOpen ? 'briefing-app-layout--open' : ''}`}>
      {isBriefing && <button type="button" className="briefing-mobile-menu"
        aria-expanded={menuOpen} onClick={() => setMenuOpen(open => !open)}>
        {menuOpen ? '关闭导航' : '打开导航'}
      </button>}
      <Sidebar />
      <div className="flex-1 ml-64">
        {children}
      </div>
    </div>
  )
}

export default Layout
