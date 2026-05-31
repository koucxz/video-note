import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import { getTaskStatus, retryTask } from '../api/client'

const STAGE_LABELS = {
  queued: '排队中',
  extracting_audio: '提取音频',
  transcribing: '语音识别',
  generating_outline: '生成大纲',
  extracting_keyframes: '提取关键帧',
  analyzing_content: '分析内容',
  generating_note: '生成笔记',
  completed: '完成'
}

function ProcessingPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const data = await getTaskStatus(taskId)
        setStatus(data)
        
        if (data.status === 'completed') {
          clearInterval(timer)
          setTimeout(() => navigate(`/note/${taskId}`), 1500)
        } else if (data.status === 'failed') {
          clearInterval(timer)
          setError(data.error)
        }
      } catch (err) {
        console.error('获取状态失败:', err)
      }
    }, 2000)

    return () => clearInterval(timer)
  }, [taskId, navigate])

  const handleRetry = async () => {
    try {
      await retryTask(taskId)
      setError(null)
      setStatus(null)
      window.location.reload()
    } catch (err) {
      alert('重试失败: ' + err.message)
    }
  }

  if (!status) {
    return (
      <div style={{ textAlign: 'center', padding: '48px' }}>
        <Loader2 size={48} className="animate-spin" color="var(--primary)" />
        <p style={{ marginTop: '16px' }}>加载中...</p>
      </div>
    )
  }

  const isCompleted = status.status === 'completed'
  const isFailed = status.status === 'failed'

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '24px', fontWeight: '600', marginBottom: '24px' }}>
        正在处理: {status.filename}
      </h1>

      <div className="card">
        {/* 进度条 */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '8px'
          }}>
            <span>{STAGE_LABELS[status.stage] || status.stage}</span>
            <span>{Math.round(status.progress * 100)}%</span>
          </div>
          <div style={{
            height: '12px',
            background: 'var(--border)',
            borderRadius: '6px',
            overflow: 'hidden'
          }}>
            <div style={{
              height: '100%',
              background: isFailed ? 'var(--error)' : isCompleted ? 'var(--success)' : 'var(--primary)',
              width: `${status.progress * 100}%`,
              transition: 'width 0.5s'
            }} />
          </div>
        </div>

        {/* 状态图标 */}
        <div style={{ textAlign: 'center', padding: '24px 0' }}>
          {isCompleted ? (
            <CheckCircle size={64} color="var(--success)" />
          ) : isFailed ? (
            <XCircle size={64} color="var(--error)" />
          ) : (
            <Loader2 size={64} className="animate-spin" color="var(--primary)" />
          )}
          
          <p style={{ marginTop: '16px', fontSize: '18px', fontWeight: '500' }}>
            {isCompleted ? '处理完成！' : isFailed ? '处理失败' : '处理中...'}
          </p>
          
          {isCompleted && (
            <p style={{ color: 'var(--text-secondary)' }}>即将跳转到笔记页面...</p>
          )}
        </div>

        {/* 错误信息 */}
        {isFailed && error && (
          <div style={{
            padding: '16px',
            background: '#fef2f2',
            borderRadius: '8px',
            marginBottom: '16px'
          }}>
            <p style={{ color: 'var(--error)', fontWeight: '500' }}>错误信息:</p>
            <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>{error}</p>
          </div>
        )}

        {/* 操作按钮 */}
        {isFailed && (
          <button
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={handleRetry}
          >
            <RefreshCw size={16} />
            重试
          </button>
        )}
      </div>
    </div>
  )
}

export default ProcessingPage
