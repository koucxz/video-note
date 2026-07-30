import { BrowserRouter, Routes, Route } from "react-router-dom"
import { LangProvider } from "./context/LangContext"
import { ToastProvider, useToast } from "./context/ToastContext"
import { setToastHandler } from "./api/client"
import ErrorBoundary from "./components/ErrorBoundary"
import Header from "./components/Header"
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

function App() {
  return (
    <ToastProvider>
      <LangProvider>
        <BrowserRouter>
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
          <ToastConnector />
        </BrowserRouter>
      </LangProvider>
    </ToastProvider>
  )
}

export default App

