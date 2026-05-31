import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { getNoteContent } from '../api/client'

function NotePage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const [note, setNote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadNote()
  }, [taskId])

  const loadNote = async () => {
    try {
      setLoading(true)
      const data = await getNoteContent(taskId)
      setNote(data)
    } catch (err) {
      setError(err.message || '加载笔记失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    const blob = new Blob([note.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${note.filename?.replace(/\.[^.]+$/, '') || 'note'}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '48px' }}>
        <Loader2 size={48} className="animate-spin" color="var(--primary)" />
        <p style={{ marginTop: '16px' }}>加载笔记中...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '48px' }}>
        <p style={{ color: 'var(--error)' }}>{error}</p>
        <button
          className="btn btn-secondary"
          style={{ marginTop: '16px' }}
          onClick={() => navigate('/')}
        >
          返回首页
        </button>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      {/* 头部操作栏 */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px'
      }}>
        <button
          className="btn btn-secondary"
          onClick={() => navigate('/history')}
        >
          <ArrowLeft size={16} />
          返回历史
        </button>
        
        <h1 style={{ fontSize: '20px', fontWeight: '600' }}>
          {note.filename}
        </h1>
        
        <button
          className="btn btn-primary"
          onClick={handleDownload}
        >
          <Download size={16} />
          下载笔记
        </button>
      </div>

      {/* 笔记内容 */}
      <div className="card" style={{ padding: '32px' }}>
        <div className="markdown-body">
          <ReactMarkdown>{note.content}</ReactMarkdown>
        </div>
      </div>

      <style>{`
        .markdown-body h1 { font-size: 24px; margin: 24px 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
        .markdown-body h2 { font-size: 20px; margin: 20px 0 12px; }
        .markdown-body h3 { font-size: 16px; margin: 16px 0 8px; }
        .markdown-body p { margin: 8px 0; line-height: 1.8; }
        .markdown-body ul, .markdown-body ol { margin: 8px 0; padding-left: 24px; }
        .markdown-body li { margin: 4px 0; }
        .markdown-body code { background: var(--bg); padding: 2px 6px; border-radius: 4px; font-size: 14px; }
        .markdown-body pre { background: var(--bg); padding: 16px; border-radius: 8px; overflow-x: auto; }
        .markdown-body blockquote { border-left: 4px solid var(--primary); padding-left: 16px; margin: 16px 0; color: var(--text-secondary); }
      `}</style>
    </div>
  )
}

export default NotePage
