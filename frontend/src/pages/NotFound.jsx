import { Link } from 'react-router-dom'

function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="text-center">
        <div className="window-dots justify-center mb-4">
          <span className="window-dot window-dot-red" />
          <span className="window-dot window-dot-yellow" />
          <span className="window-dot window-dot-green" />
        </div>
        <h1 className="text-6xl font-bold mb-2" style={{ color: 'var(--text-muted)' }}>404</h1>
        <h2 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>页面未找到</h2>
        <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>抱歉，您访问的页面不存在</p>
        <Link 
          to="/" 
          className="inline-flex items-center px-4 py-2 rounded text-sm font-medium"
          style={{ backgroundColor: 'var(--accent-blue)', color: 'white' }}
        >
          返回首页
        </Link>
      </div>
    </div>
  )
}

export default NotFound
