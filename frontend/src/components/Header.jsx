import { Link, useLocation } from 'react-router-dom'
import { useLang } from '../context/LangContext'
import { History, Upload, Sparkles, Settings, Globe, Folder } from 'lucide-react'

function Header() {
  const location = useLocation()
  const { t, lang, toggleLang } = useLang()

  return (
    <header style={{
      background: 'rgba(255,255,255,0.92)',
      borderBottom: '1px solid var(--gray-200)',
      padding: '0 24px',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      backdropFilter: 'blur(12px)',
      height: 56,
      display: 'flex',
      alignItems: 'center',
    }}>
      <div style={{
        maxWidth: 1280,
        margin: '0 auto',
        width: '100%',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <Link to="/" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          textDecoration: 'none',
          color: 'var(--gray-900)',
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 10,
            background: 'linear-gradient(135deg, var(--blue), #818cf8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Sparkles size={16} color="white" />
          </div>
          <span style={{ fontWeight: 700, fontSize: 17, letterSpacing: '-0.5px' }}>VideoNote</span>
        </Link>

        <nav style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {[
            { to: '/', icon: Upload, label: t.upload },
            { to: '/history', icon: History, label: t.history },
            { to: '/collections', icon: Folder, label: lang === 'zh' ? '合集' : 'Collections' },
            { to: '/settings', icon: Settings, label: t.settings },
          ].map(({ to, icon: Icon, label }) => (
            <Link key={to} to={to} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 8,
              textDecoration: 'none', fontSize: 14, fontWeight: 500,
              color: location.pathname === to ? 'var(--blue)' : 'var(--gray-500)',
              background: location.pathname === to ? 'var(--blue-light)' : 'transparent',
              transition: 'all 0.15s',
            }}>
              <Icon size={16} />
              <span>{label}</span>
            </Link>
          ))}

          {/* Language switch - pill style */}
          <div onClick={toggleLang} style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '6px 12px', borderRadius: 100,
            border: '1px solid var(--gray-200)',
            background: 'var(--white)',
            cursor: 'pointer', marginLeft: 8,
            fontSize: 13, fontWeight: 500, lineHeight: 1,
            color: 'var(--gray-500)',
            transition: 'all 0.15s',
            userSelect: 'none',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--blue)'; e.currentTarget.style.color = 'var(--blue)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--gray-200)'; e.currentTarget.style.color = 'var(--gray-500)'; }}
          >
            <Globe size={14} />
            <span>{lang === 'zh' ? 'EN' : '中'}</span>
          </div>
        </nav>
      </div>
    </header>
  )
}

export default Header
