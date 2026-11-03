import { useEffect, useState } from "react"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import { LangProvider } from "./context/LangContext"
import { ToastProvider, useToast } from "./context/ToastContext"
import { setToastHandler, getAuthConfig, getToken } from "./api/client"
import ErrorBoundary from "./components/ErrorBoundary"
import Header from "./components/Header"
import LoginPage from "./pages/LoginPage"
import UploadPage from "./pages/UploadPage"
import HistoryPage from "./pages/HistoryPage"
import NotePage from "./pages/NotePage"
import ProcessingPage from "./pages/ProcessingPage"
import SettingsPage from "./pages/SettingsPage"
import CollectionsPage from "./pages/CollectionsPage"
import FlashcardPage from "./pages/FlashcardPage"
import ModelConfigPage from "./pages/ModelConfigPage"
import RAGPage from "./pages/RAGPage"

function ToastConnector() {
  const toast = useToast()
  setToastHandler(toast)
  return null
}

function FullScreenLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground" />
        <span className="text-sm">加载中…</span>
      </div>
    </div>
  )
}

function MainShell() {
  return (
    <div className="relative flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<UploadPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/note/:taskId" element={<NotePage />} />
              <Route path="/processing/:taskId" element={<ProcessingPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/collections" element={<CollectionsPage />} />
              <Route path="/flashcards/:taskId" element={<FlashcardPage />} />
              <Route path="/rag" element={<RAGPage />} />
              <Route path="/settings/models" element={<ModelConfigPage />} />
            </Routes>
          </ErrorBoundary>
        </div>
      </main>
    </div>
  )
}

// 单用户登录门禁：后端未配置账号密码时直接放行（本地开发）
function AuthGate() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let alive = true

    getAuthConfig()
      .then((cfg) => {
        if (!alive) return
        setStatus(!cfg.auth_required || getToken() ? 'authed' : 'anon')
      })
      .catch(() => {
        if (!alive) return
        setStatus(getToken() ? 'authed' : 'anon')
      })

    const onUnauthorized = () => setStatus('anon')
    window.addEventListener('vn-unauthorized', onUnauthorized)
    return () => {
      alive = false
      window.removeEventListener('vn-unauthorized', onUnauthorized)
    }
  }, [])

  if (status === 'checking') return <FullScreenLoader />
  if (status === 'anon') return <LoginPage onSuccess={() => setStatus('authed')} />
  return <MainShell />
}

function App() {
  return (
    <ToastProvider>
      <LangProvider>
        <BrowserRouter>
          <AuthGate />
          <ToastConnector />
        </BrowserRouter>
      </LangProvider>
    </ToastProvider>
  )
}

export default App
