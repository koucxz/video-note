import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, Loader2, Copy, Check, CheckCircle2, FileText, Search, Pencil, Sparkles, Save, X, Brain } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { getNoteContent, getHistoryAll, downloadNotePdf, downloadNoteWord, polishNote } from '../api/client'
import { useLang } from '../context/LangContext'

function NotePage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { t } = useLang()
  const [note, setNote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [polishing, setPolishing] = useState(false)
  const [showPolish, setShowPolish] = useState(false)
  const [polishExtra, setPolishExtra] = useState('')
  const [notes, setNotes] = useState([])
  const [search, setSearch] = useState('')
  const [showCount, setShowCount] = useState(20)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const debounceTimer = useRef(null)

  useEffect(() => {
    getHistoryAll().then(list => setNotes(list.filter(i => i.status === 'completed'))).catch(err => console.warn('Failed to load notes:', err))
  }, [])

  // Debounce search
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => setDebouncedSearch(search), 300)
    return () => { if (debounceTimer.current) clearTimeout(debounceTimer.current) }
  }, [search])
  useEffect(() => { loadNote() }, [taskId])

  const loadNote = async () => {
    try { setLoading(true); setNote(null); setCopied(false); setNote(await getNoteContent(taskId)) }
    catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  const handleDownload = () => {
    if (!note) return
    const blob = new Blob([note.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url
    a.download = `${note.filename?.replace(/\.[^.]+$/, '') || 'note'}.md`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleDownloadWord = async () => {
    if (!note) return
    try { await downloadNoteWord(note.task_id, (note.filename?.replace(/\.[^.]+$/, '') || 'note') + '.docx') }
    catch (err) { console.error('Word download failed:', err) }
  }

  const handleDownloadPdf = async () => {
    if (!note) return
    try { await downloadNotePdf(note.task_id, (note.filename?.replace(/\.[^.]+$/, '') || 'note') + '.pdf') }
    catch (err) { console.error('PDF download failed:', err) }
  }

  const handleEdit = () => {
    setEditContent(note?.content || '')
    setEditMode(true)
  }

  const handleSaveEdit = async () => {
    // Save locally (update displayed content)
    setNote(prev => ({ ...prev, content: editContent }))
    setEditMode(false)
  }

  const handlePolish = async (style) => {
    if (!note) return
    setPolishing(true)
    try {
      const result = await polishNote(note.task_id, style, polishExtra)
      setNote(prev => ({ ...prev, content: result.content }))
      setShowPolish(false)
      setPolishExtra('')
    } catch (err) {
      console.error('Polish failed:', err)
    } finally {
      setPolishing(false)
    }
  }

  const handleCopy = () => {
    if (!note) return
    navigator.clipboard.writeText(note.content)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  const filtered = notes.filter(h => !debouncedSearch || h.videoName?.toLowerCase().includes(debouncedSearch.toLowerCase()))
  const displayed = filtered.slice(0, showCount)

  return (
    <div className="note-layout" style={{ display: 'flex', gap: 0, minHeight: 'calc(100vh - 56px)' }}>
      {/* 左侧笔记列表 */}
      <div className="note-sidebar" style={{
        width: 260, minWidth: 260,
        background: 'var(--white)',
        borderRight: '1px solid var(--gray-200)',
        padding: '12px 10px',
        overflowY: 'auto',
        height: 'calc(100vh - 56px)',
        position: 'sticky', top: 56,
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, padding: '0 4px', marginBottom: 2 }}>
          {t.history} <span style={{ fontWeight: 400, color: 'var(--gray-400)' }}>({filtered.length})</span>
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 8px', borderRadius: 6,
          background: 'var(--gray-100)', border: '1px solid var(--gray-200)',
        }}>
          <Search size={13} color="var(--gray-400)" />
          <input type="text" placeholder="搜索..." value={search} onChange={e => setSearch(e.target.value)}
            style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: 12, flex: 1, fontFamily: 'inherit', color: 'var(--gray-900)' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, overflowY: 'auto', flex: 1 }}>
          {displayed.map((item) => {
            const isActive = item.task_id === taskId
            return (
              <div key={item.task_id} onClick={() => navigate(`/note/${item.task_id}`)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 8px', borderRadius: 6, cursor: 'pointer',
                  background: isActive ? 'var(--blue-light)' : 'transparent',
                  border: isActive ? '1px solid var(--blue)' : '1px solid transparent',
                  transition: 'all 0.12s',
                }}>
                <CheckCircle2 size={13} color={isActive ? 'var(--blue)' : 'var(--green)'} />
                <span style={{
                  fontSize: 12, fontWeight: isActive ? 600 : 400,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  color: isActive ? 'var(--blue)' : 'var(--gray-700)',
                }}>
                  {item.videoName}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* 右侧笔记内容 */}
      <div className="note-content" style={{ flex: 1, padding: '20px 28px', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginBottom: 14, gap: 8 }}>
          {note && (
            <>
              <button className="btn btn-ghost btn-sm" onClick={() => navigate('/flashcards/' + note.task_id)}>
                <Brain size={14} /> {lang === 'zh' ? '闪卡' : 'Cards'}
              </button>
              <button className="btn btn-ghost btn-sm" onClick={handleEdit}>
                <Pencil size={14} /> {lang === 'zh' ? '编辑' : 'Edit'}
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowPolish(!showPolish)} disabled={polishing}>
                {polishing ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
                {lang === 'zh' ? '润色' : 'Polish'}
              </button>
              <button className="btn btn-outline btn-sm" onClick={handleCopy}>
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? t.copied : t.copy}
              </button>
              <button className="btn btn-ghost btn-sm" onClick={handleDownloadWord}>
                <FileText size={14} /> {lang === 'zh' ? 'Word' : 'Word'}
              </button>
              <button className="btn btn-ghost btn-sm" onClick={handleDownloadPdf}>
                <FileText size={14} /> {t.downloadPdf || 'PDF'}
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleDownload}>
                <Download size={14} /> {t.downloadMd || 'MD'}
              </button>
            </>
          )}
        </div>

        {showPolish && (
          <div style={{ padding: '12px 16px', background: 'var(--gray-50, #f9fafb)', borderRadius: 10, border: '1px solid var(--gray-200)', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
              {lang === 'zh' ? '选择润色风格' : 'Select polish style'}
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
              {[['standard', lang === 'zh' ? '标准' : 'Standard'], ['summary', lang === 'zh' ? '精简' : 'Brief'], ['academic', lang === 'zh' ? '学术' : 'Academic'], ['creative', lang === 'zh' ? '创意' : 'Creative']].map(([id, label]) => (
                <button key={id} onClick={() => handlePolish(id)} disabled={polishing}
                  style={{ padding: '5px 14px', borderRadius: 100, border: '1px solid var(--gray-200)', background: 'white', cursor: 'pointer', fontSize: 12, fontFamily: 'inherit' }}>
                  {label}
                </button>
              ))}
            </div>
            <input type="text" value={polishExtra} onChange={e => setPolishExtra(e.target.value)}
              placeholder={lang === 'zh' ? '额外要求（可选）' : 'Extra instructions (optional)'}
              style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid var(--gray-200)', fontSize: 12, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }} />
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '120px 0' }}>
            <Loader2 size={36} className="spin" color="var(--blue)" />
          </div>
        ) : !note ? (
          <div style={{ textAlign: 'center', padding: '120px 0' }}>
            <FileText size={48} color="var(--gray-300)" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--gray-400)', fontSize: 14 }}>{t.noNote}</p>
          </div>
        ) : (
          <>
            <p style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 12 }}>{note.filename}</p>
            <div className="card" style={{ padding: '24px 28px' }}>
              <div className="md">
                {editMode ? (
              <div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <button className="btn btn-primary btn-sm" onClick={handleSaveEdit}>
                    <Save size={14} /> {lang === 'zh' ? '保存' : 'Save'}
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setEditMode(false)}>
                    <X size={14} /> {lang === 'zh' ? '取消' : 'Cancel'}
                  </button>
                </div>
                <textarea value={editContent} onChange={e => setEditContent(e.target.value)}
                  style={{ width: '100%', minHeight: 400, padding: 16, borderRadius: 10, border: '1px solid var(--gray-200)', fontSize: 14, fontFamily: 'monospace', lineHeight: 1.6, resize: 'vertical', outline: 'none', boxSizing: 'border-box' }} />
              </div>
            ) : (
              <ReactMarkdown>{note.content}</ReactMarkdown>
            )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default NotePage
