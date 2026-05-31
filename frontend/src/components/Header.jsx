import { Link, useLocation } from 'react-router-dom'
import { Video, History, Upload, Sparkles } from 'lucide-react'

function Header() {
  const location = useLocation()
  
  return (
    <header style={{
      background: 'var(--card-bg)',
      borderBottom: '1px solid var(--border)',
      padding: '14px 0',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      backdropFilter: 'blur(8px)',
      backgroundColor: 'rgba(255,255,255,0.9)'
    }}>
      <div className="container" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Link to="/" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          textDecoration: 'none',
          color: 'var(--text)'
        }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: 'linear-gradient(135deg, var(--primary), #8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Sparkles size={20} color="white" />
          </div>
          <span style={{ fontSize: '18px', fontWeight: '700', letterSpacing: '-0.5px' }}>VideoNote</span>
        </Link>
        
        <nav style={{ display: 'flex', gap: '8px' }}>
          <Link
            to="/"
            className={`btn ${location.pathname === '/' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Upload size={16} />
            上传
          </Link>
          <Link
            to="/history"
            className={`btn ${location.pathname === '/history' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <History size={16} />
            历史
          </Link>
        </nav>
      </div>
    </header>
  )
}

export default Header
