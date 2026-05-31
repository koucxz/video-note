import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, RefreshCw, ArrowLeft } from 'lucide-react'
import { getTaskStatus, retryTask } from '../api/client'
import StageProgress from '../components/StageProgress'
import { useLang } from '../context/LangContext'

function ProcessingPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { t } = useLang()
  const [status, setStatus] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const maxRetries = 3
  const retryingRef = useRef(false)

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const data = await getTaskStatus(taskId)
        setStatus(data)
        if (data.status === 'completed') {
          clearInterval(timer)
          setTimeout(() => navigate(`/note/${taskId}`), 2000)
        } else if (data.status === 'failed') {
          clearInterval(timer)
          if (retryCount < maxRetries && !retryingRef.current) {
            retryingRef.current = true
            setRetryCount(prev => prev + 1)
            setTimeout(async () => {
              try { await retryTask(taskId); retryingRef.current = false; window.location.reload() }
              catch (err) { retryingRef.current = false }
            }, 3000)
          }
        }
      } catch (err) { console.error(err) }
    }, 2000)
    return () => clearInterval(timer)
  }, [taskId, navigate, retryCount])

  const handleManualRetry = async () => {
    try { await retryTask(taskId); setRetryCount(0); window.location.reload() }
    catch (err) { alert(t.retryFailed) }
  }

  if (!status) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <Loader2 size={36} className="animate-spin" color="var(--primary)" />
    </div>
  )

  const isCompleted = status.status === 'completed'
  const isFailed = status.status === 'failed'
  const isAutoRetrying = isFailed && retryCount < maxRetries && retryCount > 0

  return (
    <div style={{ maxWidth: '640px' }}>
      <button className="btn btn-ghost btn-sm" style={{ marginBottom: '20px' }}
        onClick={() => navigate('/history')}>
        <ArrowLeft size={16} /> {t.back}
      </button>

      <h1 className="page-title" style={{ fontSize: '18px', marginBottom: '6px', wordBreak: 'break-all' }}>
        {status.filename}
      </h1>
      <p className="page-subtitle" style={{ marginBottom: '28px' }}>
        {isCompleted ? t.completed : isFailed ? (isAutoRetrying ? `${t.autoRetry} (${retryCount}/${maxRetries})` : t.processFailed) : t.processingWait}
      </p>

      <div className="card" style={{ padding: '28px 20px' }}>
        <StageProgress currentStage={status.stage} status={status.status} />
      </div>

      <div className={`status-box ${isCompleted ? 'success' : isFailed ? 'error' : 'info'}`} style={{ marginTop: '16px' }}>
        {isCompleted ? (
          <div>
            <div style={{ fontSize: '36px', marginBottom: '8px' }}>🎉</div>
            <p style={{ fontWeight: '600', color: 'var(--success)' }}>{t.processComplete}</p>
          </div>
        ) : isFailed ? (
          isAutoRetrying ? (
            <div>
              <Loader2 size={28} className="animate-spin" color="var(--primary)" />
              <p style={{ marginTop: '10px', fontWeight: '500', color: 'var(--primary)' }}>
                {t.autoRetry} ({retryCount}/{maxRetries})
              </p>
            </div>
          ) : (
            <div>
              <p style={{ fontWeight: '500', color: 'var(--error)', marginBottom: '10px' }}>{t.processFailed}</p>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>{status.error}</p>
              <button className="btn btn-primary" onClick={handleManualRetry}>
                <RefreshCw size={16} /> {t.retry}
              </button>
            </div>
          )
        ) : (
          <Loader2 size={28} className="animate-spin" color="var(--primary)" />
        )}
      </div>
    </div>
  )
}

export default ProcessingPage
