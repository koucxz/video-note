import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Loader2, Copy, Check } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { getNoteContent } from '../api/client'
import { useLang } from '../context/LangContext'

function NotePage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { t } = useLang()
  const [note, setNote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => { loadNote() }, [taskId])

  const loadNote = async () => {
    try { setLoading(true); setNote(await getNoteContent(taskId)) }
    catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  const handleDownload = () => {
    const blob = new Blob([note.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url
    a.download = `${note.filename?.replace(/\.[^.]+$/, '') || 'note'}.md`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(note.content)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  if (loading) return <div style={{ textAlign: 'center', padding: '120px 0' }}><Loader2 size={36} className="animate-spin" color="var(--primary)" /></div>

  if (!note) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <p style={{ color: 'var(--error)' }}>{t.noNote}</p>
      <button className="btn btn-secondary" style={{ marginTop: '16px' }} onClick={() => navigate('/')}>{t.back}</button>
    </div>
  )

  return (
    <div style={{ maxWidth: '780px' }}>
      {/* 操作栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/history')}>
          <ArrowLeft size={16} /> {t.back}
        </button>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleCopy}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? t.copied : t.copy}
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleDownload}>
            <Download size={14} /> {t.download}
          </button>
        </div>
      </div>

      {/* 文件名 */}
      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '14px' }}>{note.filename}</p>

      {/* 笔记内容 */}
      <div className="card" style={{ padding: '28px 32px' }}>
        <div className="markdown-body">
          <ReactMarkdown>{note.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

export default NotePage
