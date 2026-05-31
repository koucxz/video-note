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
          // 自动重试
          if (retryCount < maxRetries && !retryingRef.current) {
            retryingRef.current = true
            setRetryCount(prev => prev + 1)
            setTimeout(async () => {
              try {
                await retryTask(taskId)
                retryingRef.current = false
                // 重新开始轮询
                window.location.reload()
              } catch (err) {
                retryingRef.current = false
                console.error('Auto retry failed:', err)
              }
            }, 3000)
          }
        }
      } catch (err) {
        console.error(err)
      }
    }, 2000)

    return () => clearInterval(timer)
  }, [taskId, navigate, retryCount])

  const handleManualRetry = async () => {
    try {
      await retryTask(taskId)
      setRetryCount(0)
      window.location.reload()
    } catch (err) {
      alert(t.retryFailed + ': ' + err.message)
    }
  }

  if (!status) {
    return (
      <div style={{ textAlign: 'center', padding: '120px 0' }}>
        <Loader2 size={40} className="animate-spin" color="var(--primary)" />
      </div>
    )
  }

  const isCompleted = status.status === 'completed'
  const isFailed = status.status === 'failed'
  const isAutoRetrying = isFailed && retryCount < maxRetries && retryCount > 0

  return (
    <div style={{ maxWidth: '700px' }}>
      <button className="btn btn-ghost btn-sm" style={{ marginBottom: '20px' }}
        onClick={() => navigate('/history')}>
        <ArrowLeft size={16} /> {t.back}
      </button>

      <h1 className="page-title" style={{ marginBottom: '8px', fontSize: '18px' }}>
        {status.filename}
      </h1>
      <p className="page-subtitle" style={{ marginBottom: '32px' }}>
        {isCompleted ? t.completed : isFailed ? (isAutoRetrying ? `${t.autoRetry} (${retryCount}/${maxRetries})` : t.processFailed) : t.processingWait}
      </p>

      {/* 横向进度条 */}
      <div className="card" style={{ padding: '32px 24px' }}>
        <StageProgress currentStage={status.stage} status={status.status} />
      </div>

      {/* 状态消息 */}
      <div className="card" style={{ marginTop: '16px', textAlign: 'center', padding: '32px' }}>
        {isCompleted ? (
          <div>
            <div style={{ fontSize: '40px', marginBottom: '12px' }}>🎉</div>
            <p style={{ fontWeight: '600', fontSize: '16px', color: 'var(--success)' }}>{t.processComplete}</p>
          </div>
        ) : isFailed ? (
          <div>
            {isAutoRetrying ? (
              <>
                <Loader2 size={32} className="animate-spin" color="var(--primary)" />
                <p style={{ marginTop: '12px', fontWeight: '500', color: 'var(--primary)' }}>
                  {t.autoRetry} ({retryCount}/{maxRetries})
                </p>
              </>
            ) : (
              <>
                <p style={{ fontWeight: '500', color: 'var(--error)', marginBottom: '12px' }}>{t.processFailed}</p>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>{status.error}</p>
                <button className="btn btn-primary" onClick={handleManualRetry}>
                  <RefreshCw size={16} /> {t.retry}
                </button>
              </>
            )}
          </div>
        ) : (
          <Loader2 size={32} className="animate-spin" color="var(--primary)" />
        )}
      </div>
    </div>
  )
}

export default ProcessingPage
