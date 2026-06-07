import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, RefreshCw, ArrowLeft, Wifi, AlertTriangle, FileQuestion, Scissors } from 'lucide-react'
import { getTaskStatus, retryTask, cancelTask } from '../api/client'
import { useTaskWebSocket } from '../hooks/useWebSocket'
import StageProgress from '../components/StageProgress'
import { useLang } from '../context/LangContext'

const ERROR_KIND_MESSAGES = {
  zh: {
    network: { icon: 'Wifi', title: '网络连接失败', hint: '请检查网络或 API 服务是否可用' },
    api: { icon: 'AlertTriangle', title: 'AI 服务错误', hint: 'API 密钥无效或服务暂时不可用' },
    ffmpeg: { icon: 'Scissors', title: '视频处理失败', hint: '视频格式可能不支持，或 FFmpeg 未安装' },
    format: { icon: 'FileQuestion', title: '文件格式问题', hint: '视频文件可能已损坏或格式不支持' },
    interrupted: { icon: 'RefreshCw', title: '处理被中断', hint: '服务可能重启过，点击重试继续' },
    unknown: { icon: 'AlertTriangle', title: '处理失败', hint: '发生未知错误，请重试' },
  },
  en: {
    network: { icon: 'Wifi', title: 'Network Error', hint: 'Check your network or API availability' },
    api: { icon: 'AlertTriangle', title: 'AI Service Error', hint: 'Invalid API key or service unavailable' },
    ffmpeg: { icon: 'Scissors', title: 'Processing Failed', hint: 'Video format may be unsupported or FFmpeg missing' },
    format: { icon: 'FileQuestion', title: 'Format Issue', hint: 'Video file may be corrupt or unsupported' },
    interrupted: { icon: 'RefreshCw', title: 'Interrupted', hint: 'Service may have restarted. Retry to continue.' },
    unknown: { icon: 'AlertTriangle', title: 'Failed', hint: 'An unknown error occurred. Please retry.' },
  },
}

function ProcessingPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const [status, setStatus] = useState(null)
  const wsStatus = useTaskWebSocket(taskId)
  const [retryCount, setRetryCount] = useState(0)
  const maxRetries = 3
  const retryingRef = useRef(false)

  // Sync WebSocket updates
  useEffect(() => {
    if (wsStatus && wsStatus.status) {
      setStatus(prev => ({ ...prev, ...wsStatus }));
      if (wsStatus.status === 'completed') {
        setTimeout(() => navigate(`/note/${taskId}`), 2000);
      }
    }
  }, [wsStatus, taskId, navigate]);

  // Fallback polling (slower interval)
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
          if (data.error_kind !== 'interrupted' && retryCount < maxRetries && !retryingRef.current) {
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

  const handleCancel = async () => {
    try { await cancelTask(taskId); navigate('/history'); }
    catch (err) { alert(t.cancelFailed || 'Cancel failed'); }
  }

  const handleManualRetry = async () => {
    try { await retryTask(taskId); setRetryCount(0); window.location.reload() }
    catch (err) { alert(t.retryFailed) }
  }

  if (!status) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <Loader2 size={36} className="spin" color="var(--blue)" />
    </div>
  )

  const isCompleted = status.status === 'completed'
  const isFailed = status.status === 'failed'
  const isAutoRetrying = isFailed && retryCount < maxRetries && retryCount > 0
  const errorKind = status.error_kind || 'unknown'
  const errorInfo = ERROR_KIND_MESSAGES[lang]?.[errorKind] || ERROR_KIND_MESSAGES.zh[errorKind] || ERROR_KIND_MESSAGES.zh.unknown

  return (
    <div style={{ maxWidth: 640 }}>
      <button className="btn btn-ghost btn-sm" style={{ marginBottom: 20 }}
        onClick={() => navigate('/history')}>
        <ArrowLeft size={16} /> {t.back}
      </button>

      <div className="card" style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 6, wordBreak: 'break-all' }}>
          {status.filename}
        </h1>
        <p style={{ color: 'var(--gray-400)', fontSize: 13, marginBottom: 20 }}>
          {isCompleted ? t.completed : isFailed ? (isAutoRetrying ? `${t.autoRetry} (${retryCount}/${maxRetries})` : errorInfo.title) : t.processingWait}
        </p>
        <StageProgress currentStage={status.stage} status={status.status} />
      </div>

      <div className="status-panel" style={{
        background: isCompleted ? 'var(--green-light)' : isFailed ? 'var(--red-light)' : 'var(--blue-light)',
        borderRadius: 'var(--radius-lg)',
        padding: 24,
      }}>
        {isCompleted ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 36, marginBottom: 8 }}>&#127881;</div>
            <p style={{ fontWeight: 600, color: 'var(--green)' }}>{t.processComplete}</p>
          </div>
        ) : isFailed ? (
          isAutoRetrying ? (
            <div style={{ textAlign: 'center' }}>
              <Loader2 size={28} className="spin" color="var(--blue)" />
              <p style={{ marginTop: 10, fontWeight: 500, color: 'var(--blue)' }}>
                {t.autoRetry} ({retryCount}/{maxRetries})
              </p>
            </div>
          ) : (
            <div style={{ textAlign: 'center' }}>
              <p style={{ fontWeight: 600, color: 'var(--red)', fontSize: 15, marginBottom: 6 }}>
                {errorInfo.title}
              </p>
              <p style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 12 }}>
                {errorInfo.hint}
              </p>
              {status.error && (
                <details style={{ fontSize: 11, color: 'var(--gray-400)', marginBottom: 16, textAlign: 'left', maxWidth: 400, margin: '0 auto 16px' }}>
                  <summary style={{ cursor: 'pointer' }}>{lang === 'zh' ? '技术详情' : 'Technical details'}</summary>
                  <pre style={{ marginTop: 6, padding: 8, background: 'var(--gray-100)', borderRadius: 6, fontSize: 11, overflow: 'auto', maxHeight: 120 }}>{status.error}</pre>
                </details>
              )}
              <button className="btn btn-primary" onClick={handleManualRetry}>
                <RefreshCw size={16} /> {t.retry}
              </button>
            </div>
          )
        ) : (
          <div style={{ textAlign: 'center' }}>
            <Loader2 size={28} className="spin" color="var(--blue)" />
            <button className="btn btn-ghost btn-sm" style={{ marginTop: 12 }} onClick={handleCancel}>
              {t.cancel || 'Cancel'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default ProcessingPage
