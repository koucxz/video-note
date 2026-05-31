import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react'
import { getTaskStatus, retryTask } from '../api/client'
import StageProgress from '../components/StageProgress'

function ProcessingPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)

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
        }
      } catch (err) {
        console.error('Status error:', err)
      }
    }, 2000)

    return () => clearInterval(timer)
  }, [taskId, navigate])

  const handleRetry = async () => {
    try {
      await retryTask(taskId)
      setStatus(null)
      window.location.reload()
    } catch (err) {
      alert('Retry failed: ' + err.message)
    }
  }

  if (!status) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Loader2 size={48} className="animate-spin" color="var(--primary)" />
        <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>加载中...</p>
      </div>
    )
  }

  const isCompleted = status.status === 'completed'
  const isFailed = status.status === 'failed'

  return (
    <div style={{ maxWidth: '480px', margin: '0 auto' }}>
      {/* 返回按钮 */}
      <button 
        className="btn btn-secondary" 
        style={{ marginBottom: '24px' }}
        onClick={() => navigate('/history')}
      >
        <ArrowLeft size={16} />
        返回历史
      </button>

      {/* 文件名 */}
      <h1 style={{ 
        fontSize: '20px', 
        fontWeight: '600', 
        marginBottom: '24px',
        wordBreak: 'break-all'
      }}>
        {status.filename}
      </h1>

      {/* 进度卡片 */}
      <div className="card">
        <StageProgress currentStage={status.stage} status={status.status} />
        
        {/* 状态消息 */}
        <div style={{ 
          marginTop: '24px', 
          padding: '16px',
          borderRadius: '12px',
          background: isCompleted ? 'var(--success-light)' : 
                     isFailed ? 'var(--error-light)' : 'var(--bg)',
          textAlign: 'center'
        }}>
          {isCompleted ? (
            <div>
              <div style={{ fontSize: '24px', marginBottom: '8px' }}>🎉</div>
              <p style={{ fontWeight: '500', color: 'var(--success)' }}>
                处理完成！正在跳转到笔记...
              </p>
            </div>
          ) : isFailed ? (
            <div>
              <p style={{ fontWeight: '500', color: 'var(--error)', marginBottom: '12px' }}>
                处理失败
              </p>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                {status.error || '未知错误'}
              </p>
              <button className="btn btn-primary" onClick={handleRetry}>
                <RefreshCw size={16} />
                重试
              </button>
            </div>
          ) : (
            <p style={{ color: 'var(--text-secondary)' }}>
              正在处理中，请稍候...
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProcessingPage
