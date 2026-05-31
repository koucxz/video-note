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
    const a = document.createElement('a')
    a.href = url; a.download = `${note.filename?.replace(/\.[^.]+$/, '') || 'note'}.md`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(note.content)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  if (loading) return <div style={{ textAlign: 'center', padding: '120px 0' }}><Loader2 size={40} className="animate-spin" color="var(--primary)" /></div>

  if (!note) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <p style={{ color: 'var(--error)' }}>{t.noNote}</p>
      <button className="btn btn-secondary" style={{ marginTop: '16px' }} onClick={() => navigate('/')}>{t.back}</button>
    </div>
  )

  return (
    <div style={{ maxWidth: '800px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <button className="btn btn-ghost" onClick={() => navigate('/history')}>
          <ArrowLeft size={16} /> {t.back}
        </button>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleCopy}>
            {copied ? <Check size={16} /> : <Copy size={16} />} {copied ? t.copied : t.copy}
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleDownload}>
            <Download size={16} /> {t.download}
          </button>
        </div>
      </div>

      <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>{note.filename}</p>

      <div className="card" style={{ padding: '32px' }}>
        <div className="markdown-body">
          <ReactMarkdown>{note.content}</ReactMarkdown>
        </div>
      </div>

      <style>{`
        .markdown-body h1 { font-size: 22px; margin: 28px 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); font-weight: 700; }
        .markdown-body h1:first-child { margin-top: 0; }
        .markdown-body h2 { font-size: 17px; margin: 24px 0 12px; font-weight: 600; color: var(--primary); }
        .markdown-body h3 { font-size: 15px; margin: 20px 0 8px; font-weight: 600; }
        .markdown-body p { margin: 10px 0; line-height: 1.8; }
        .markdown-body ul, .markdown-body ol { margin: 10px 0; padding-left: 24px; }
        .markdown-body li { margin: 6px 0; line-height: 1.7; }
        .markdown-body strong { font-weight: 600; }
        .markdown-body code { background: var(--primary-light); padding: 2px 6px; border-radius: 6px; font-size: 13px; }
        .markdown-body blockquote { border-left: 3px solid var(--primary); padding: 12px 16px; margin: 16px 0; background: var(--primary-light); border-radius: 0 8px 8px 0; }
        .markdown-body hr { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
      `}</style>
    </div>
  )
}

export default NotePage
