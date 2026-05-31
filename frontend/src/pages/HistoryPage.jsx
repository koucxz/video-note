import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, Eye, RefreshCw, Loader2, Clock, CheckCircle2, XCircle, History, ArrowUpRight } from 'lucide-react'
import { getHistory, deleteTask, retryTask } from '../api/client'
import { useLang } from '../context/LangContext'

function HistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { t } = useLang()

  useEffect(() => { loadHistory() }, [])

  const loadHistory = async () => {
    try { setLoading(true); setHistory(await getHistory()) }
    catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  const handleDelete = async (e, taskId) => {
    e.stopPropagation()
    if (!confirm(t.confirmDelete)) return
    try { await deleteTask(taskId); setHistory(history.filter(i => i.task_id !== taskId)) }
    catch (err) { alert(t.deleteFailed) }
  }

  const handleRetry = async (e, taskId) => {
    e.stopPropagation()
    try { await retryTask(taskId); loadHistory() }
    catch (err) { alert(t.retryFailed) }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const mins = Math.floor((Date.now() - new Date(dateStr)) / 60000)
    if (mins < 1) return t.justNow
    if (mins < 60) return `${mins} ${t.minsAgo}`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours} ${t.hoursAgo}`
    return `${Math.floor(hours / 24)} ${t.daysAgo}`
  }

  const statusMap = {
    completed: { icon: CheckCircle2, color: 'var(--success)', bg: 'var(--success-light)', label: t.completed },
    failed: { icon: XCircle, color: 'var(--error)', bg: 'var(--error-light)', label: t.failed },
    processing: { icon: Loader2, color: 'var(--primary)', bg: 'var(--primary-light)', label: t.processing },
    pending: { icon: Clock, color: 'var(--text-muted)', bg: 'var(--bg)', label: t.pending },
  }

  if (loading) return <div style={{ textAlign: 'center', padding: '120px 0' }}><Loader2 size={36} className="animate-spin" color="var(--primary)" /></div>

  return (
    <div style={{ maxWidth: '680px' }}>
      <div className="page-header">
        <h1 className="page-title">{t.history}</h1>
        <p className="page-subtitle">{t.totalRecords} {history.length} {t.records}</p>
      </div>

      {history.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '56px 24px' }}>
          <div style={{ width: 56, height: 56, borderRadius: 16, background: 'var(--primary-light)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px' }}>
            <History size={28} color="var(--primary)" />
          </div>
          <p style={{ fontWeight: '600', fontSize: '15px', marginBottom: '4px' }}>{t.noRecords}</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '20px' }}>{t.uploadFirst}</p>
          <button className="btn btn-primary" onClick={() => navigate('/')}>{t.upload}</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {history.map((item) => {
            const s = statusMap[item.status] || statusMap.pending
            const Icon = s.icon
            return (
              <div key={item.task_id} className="history-item animate-in"
                onClick={() => item.status === 'completed' && navigate(`/note/${item.task_id}`)}>
                <div className="history-icon" style={{ background: s.bg }}>
                  <Icon size={20} color={s.color} className={item.status === 'processing' ? 'animate-spin' : ''} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '14px', fontWeight: '500', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.videoName}
                  </div>
                  <div style={{ display: 'flex', gap: '8px', fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>
                    <span>{formatDate(item.createdAt)}</span>
                    <span style={{ color: s.color }}>{s.label}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                  {item.status === 'completed' && (
                    <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); navigate(`/note/${item.task_id}`) }}>
                      <ArrowUpRight size={14} /> {t.view}
                    </button>
                  )}
                  {item.status === 'failed' && (
                    <button className="btn btn-ghost btn-sm" onClick={(e) => handleRetry(e, item.task_id)}>
                      <RefreshCw size={14} />
                    </button>
                  )}
                  <button className="btn btn-ghost btn-sm" style={{ color: 'var(--text-muted)' }} onClick={(e) => handleDelete(e, item.task_id)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default HistoryPage
