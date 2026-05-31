import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Upload, History, Sparkles, Languages, Globe } from 'lucide-react'
import { LangProvider, useLang } from './context/LangContext'
import UploadPage from './pages/UploadPage'
import ProcessingPage from './pages/ProcessingPage'
import HistoryPage from './pages/HistoryPage'
import NotePage from './pages/NotePage'

function Sidebar() {
  const location = useLocation()
  const { lang, toggleLang, t } = useLang()
  
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">V</div>
        <div>
          <div className="sidebar-logo-text">{t.appName}</div>
          <div className="sidebar-logo-desc">{t.appDesc}</div>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        <Link to="/" className={`sidebar-link ${location.pathname === '/' ? 'active' : ''}`}>
          <Upload size={18} />
          <span>{t.upload}</span>
        </Link>
        <Link to="/history" className={`sidebar-link ${location.pathname.startsWith('/history') || location.pathname.startsWith('/note') || location.pathname.startsWith('/processing') ? 'active' : ''}`}>
          <History size={18} />
          <span>{t.history}</span>
        </Link>
      </nav>
      
      <div className="sidebar-footer">
        <button className="lang-toggle" onClick={toggleLang}>
          <Globe size={16} />
          <span>{lang === 'zh' ? '中文' : 'English'}</span>
          <span className="lang-badge">{lang === 'zh' ? 'EN' : '中'}</span>
        </button>
      </div>
    </aside>
  )
}

function App() {
  return (
    <LangProvider>
      <BrowserRouter>
        <div className="app-layout">
          <Sidebar />
          <main className="main-content animate-in">
            <Routes>
              <Route path="/" element={<UploadPage />} />
              <Route path="/processing/:taskId" element={<ProcessingPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/note/:taskId" element={<NotePage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </LangProvider>
  )
}

export default App
