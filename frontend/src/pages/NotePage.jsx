import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Loader2, Copy, Check } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { getNoteContent } from '../api/client'

function NotePage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const [note, setNote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => { loadNote() }, [taskId])

  const loadNote = async () => {
    try {
      setLoading(true)
      const data = await getNoteContent(taskId)
      setNote(data)
    } catch (err) {
      console.error(err)
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

  const handleCopy = () => {
    navigator.clipboard.writeText(note.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Loader2 size={40} className="animate-spin" color="var(--primary)" />
        <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>加载笔记中...</p>
      </div>
    )
  }

  if (!note) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <p style={{ color: 'var(--error)' }}>笔记不存在</p>
        <button className="btn btn-secondary" style={{ marginTop: '16px' }} onClick={() => navigate('/')}>
          返回首页
        </button>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      {/* 顶部操作栏 */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <button className="btn btn-secondary" onClick={() => navigate('/history')}>
          <ArrowLeft size={16} />
          返回
        </button>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={handleCopy}>
            {copied ? <Check size={16} /> : <Copy size={16} />}
            {copied ? '已复制' : '复制'}
          </button>
          <button className="btn btn-primary" onClick={handleDownload}>
            <Download size={16} />
            下载
          </button>
        </div>
      </div>

      {/* 文件名 */}
      <h1 style={{ 
        fontSize: '18px', 
        fontWeight: '600', 
        color: 'var(--text-secondary)',
        marginBottom: '20px'
      }}>
        {note.filename}
      </h1>

      {/* 笔记内容 */}
      <div className="card" style={{ padding: '32px' }}>
        <div className="markdown-body">
          <ReactMarkdown>{note.content}</ReactMarkdown>
        </div>
      </div>

      <style>{`
        .markdown-body h1 { font-size: 22px; margin: 28px 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); font-weight: 700; }
        .markdown-body h1:first-child { margin-top: 0; }
        .markdown-body h2 { font-size: 18px; margin: 24px 0 12px; font-weight: 600; color: var(--primary); }
        .markdown-body h3 { font-size: 16px; margin: 20px 0 8px; font-weight: 600; }
        .markdown-body p { margin: 10px 0; line-height: 1.8; }
        .markdown-body ul, .markdown-body ol { margin: 10px 0; padding-left: 24px; }
        .markdown-body li { margin: 6px 0; line-height: 1.7; }
        .markdown-body strong { color: var(--text); font-weight: 600; }
        .markdown-body code { background: var(--bg); padding: 2px 6px; border-radius: 6px; font-size: 13px; font-family: 'JetBrains Mono', monospace; }
        .markdown-body pre { background: var(--bg); padding: 16px; border-radius: 12px; overflow-x: auto; margin: 16px 0; }
        .markdown-body blockquote { border-left: 4px solid var(--primary); padding: 12px 16px; margin: 16px 0; background: var(--primary-light); border-radius: 0 8px 8px 0; }
        .markdown-body hr { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
      `}</style>
    </div>
  )
}

export default NotePage
