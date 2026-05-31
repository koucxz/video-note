import { Link, useLocation } from 'react-router-dom'
import { Video, History, Upload } from 'lucide-react'

function Header() {
  const location = useLocation()
  
  return (
    <header style={{
      background: 'var(--card-bg)',
      borderBottom: '1px solid var(--border)',
      padding: '16px 0'
    }}>
      <div className="container" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Link to="/" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          textDecoration: 'none',
          color: 'var(--text)'
        }}>
          <Video size={24} color="var(--primary)" />
          <span style={{ fontSize: '20px', fontWeight: '600' }}>VideoNote</span>
        </Link>
        
        <nav style={{ display: 'flex', gap: '16px' }}>
          <Link
            to="/"
            className={`btn ${location.pathname === '/' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Upload size={16} />
            上传视频
          </Link>
          <Link
            to="/history"
            className={`btn ${location.pathname === '/history' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <History size={16} />
            历史记录
          </Link>
        </nav>
      </div>
    </header>
  )
}

export default Header
