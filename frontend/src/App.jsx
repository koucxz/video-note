import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import UploadPage from './pages/UploadPage'
import ProcessingPage from './pages/ProcessingPage'
import HistoryPage from './pages/HistoryPage'
import NotePage from './pages/NotePage'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Header />
        <main className="container" style={{ paddingTop: '24px', paddingBottom: '48px' }}>
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/processing/:taskId" element={<ProcessingPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/note/:taskId" element={<NotePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
