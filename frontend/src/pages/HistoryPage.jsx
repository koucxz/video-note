import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, Eye, RefreshCw, Loader2, Clock, CheckCircle2, XCircle, History } from 'lucide-react'
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

  const handleDelete = async (taskId) => {
    if (!confirm(t.confirmDelete)) return
    try { await deleteTask(taskId); setHistory(history.filter(t => t.task_id !== taskId)) }
    catch (err) { alert(t.deleteFailed + ': ' + err.message) }
  }

  const handleRetry = async (taskId) => {
    try { await retryTask(taskId); loadHistory() }
    catch (err) { alert(t.retryFailed + ': ' + err.message) }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr); const now = new Date()
    const mins = Math.floor((now - d) / 60000)
    if (mins < 1) return t.justNow
    if (mins < 60) return `${mins} ${t.minsAgo}`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours} ${t.hoursAgo}`
    return `${Math.floor(hours / 24)} ${t.daysAgo}`
  }

  const statusConfig = {
    completed: { icon: CheckCircle2, color: 'var(--success)', bg: 'var(--success-light)', label: t.completed },
    failed: { icon: XCircle, color: 'var(--error)', bg: 'var(--error-light)', label: t.failed },
    processing: { icon: Loader2, color: 'var(--primary)', bg: 'var(--primary-light)', label: t.processing },
    pending: { icon: Clock, color: 'var(--text-muted)', bg: 'var(--bg)', label: t.pending },
  }

  if (loading) return <div style={{ textAlign: 'center', padding: '120px 0' }}><Loader2 size={40} className="animate-spin" color="var(--primary)" /></div>

  return (
    <div style={{ maxWidth: '700px' }}>
      <div className="page-header">
        <h1 className="page-title">{t.history}</h1>
        <p className="page-subtitle">{t.totalRecords} {history.length} {t.records}</p>
      </div>

      {history.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
          <div style={{ width: 64, height: 64, borderRadius: 20, background: 'var(--primary-light)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <History size={32} color="var(--primary)" />
          </div>
          <p style={{ fontWeight: '500', marginBottom: '4px' }}>{t.noRecords}</p>
          <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>{t.uploadFirst}</p>
          <button className="btn btn-primary" onClick={() => navigate('/')}>{t.upload}</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {history.map((item) => {
            const config = statusConfig[item.status] || statusConfig.pending
            const StatusIcon = config.icon
            return (
              <div key={item.task_id} className="card animate-in" style={{
                padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px',
                cursor: item.status === 'completed' ? 'pointer' : 'default'
              }} onClick={() => item.status === 'completed' && navigate(`/note/${item.task_id}`)}>
                <div style={{ width: 40, height: 40, borderRadius: 10, background: config.bg,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <StatusIcon size={20} color={config.color} className={item.status === 'processing' ? 'animate-spin' : ''} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: '500', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.videoName}
                  </div>
                  <div style={{ display: 'flex', gap: '10px', fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    <span>{formatDate(item.createdAt)}</span>
                    <span style={{ color: config.color }}>{config.label}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '4px' }} onClick={e => e.stopPropagation()}>
                  {item.status === 'completed' && (
                    <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/note/${item.task_id}`)}>
                      <Eye size={16} /> {t.view}
                    </button>
                  )}
                  {item.status === 'failed' && (
                    <button className="btn btn-ghost btn-sm" onClick={() => handleRetry(item.task_id)}>
                      <RefreshCw size={16} />
                    </button>
                  )}
                  <button className="btn btn-ghost btn-sm" style={{ color: 'var(--error)' }}
                    onClick={() => handleDelete(item.task_id)}>
                    <Trash2 size={16} />
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
