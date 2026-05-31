import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Trash2, Eye, RefreshCw, Loader2, Clock, CheckCircle2, XCircle, History } from 'lucide-react'
import { getHistory, deleteTask, retryTask } from '../api/client'

function HistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => { loadHistory() }, [])

  const loadHistory = async () => {
    try {
      setLoading(true)
      const data = await getHistory()
      setHistory(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (taskId) => {
    if (!confirm('确定要删除这条记录吗？')) return
    try {
      await deleteTask(taskId)
      setHistory(history.filter(t => t.task_id !== taskId))
    } catch (err) {
      alert('删除失败: ' + err.message)
    }
  }

  const handleRetry = async (taskId) => {
    try {
      await retryTask(taskId)
      loadHistory()
    } catch (err) {
      alert('重试失败: ' + err.message)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    const now = new Date()
    const diff = now - d
    const mins = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    
    if (mins < 1) return '刚刚'
    if (mins < 60) return `${mins} 分钟前`
    if (hours < 24) return `${hours} 小时前`
    if (days < 7) return `${days} 天前`
    return d.toLocaleDateString('zh-CN')
  }

  const getStatusConfig = (status) => {
    switch (status) {
      case 'completed': return { icon: CheckCircle2, color: 'var(--success)', bg: 'var(--success-light)', label: '已完成' }
      case 'failed': return { icon: XCircle, color: 'var(--error)', bg: 'var(--error-light)', label: '失败' }
      case 'processing': return { icon: Loader2, color: 'var(--primary)', bg: 'var(--primary-light)', label: '处理中' }
      default: return { icon: Clock, color: 'var(--text-secondary)', bg: 'var(--bg)', label: '等待中' }
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Loader2 size={40} className="animate-spin" color="var(--primary)" />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '700px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '700' }}>历史记录</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
          共 {history.length} 条记录
        </p>
      </div>

      {history.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
          <div style={{
            width: 64, height: 64, borderRadius: 20, background: 'var(--bg)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <History size={32} color="var(--text-secondary)" />
          </div>
          <p style={{ fontWeight: '500', marginBottom: '4px' }}>暂无记录</p>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>上传你的第一个视频开始吧</p>
          <button className="btn btn-primary" onClick={() => navigate('/')}>上传视频</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {history.map((item) => {
            const config = getStatusConfig(item.status)
            const StatusIcon = config.icon
            
            return (
              <div 
                key={item.task_id} 
                className="card" 
                style={{ 
                  padding: '16px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  cursor: item.status === 'completed' ? 'pointer' : 'default',
                  transition: 'all 0.2s'
                }}
                onClick={() => item.status === 'completed' && navigate(`/note/${item.task_id}`)}
              >
                {/* 状态图标 */}
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: config.bg,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <StatusIcon 
                    size={22} 
                    color={config.color} 
                    className={item.status === 'processing' ? 'animate-spin' : ''}
                  />
                </div>
                
                {/* 信息 */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    fontWeight: '500', 
                    fontSize: '15px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    marginBottom: '4px'
                  }}>
                    {item.videoName}
                  </div>
                  <div style={{ 
                    display: 'flex', 
                    gap: '12px', 
                    fontSize: '13px',
                    color: 'var(--text-secondary)' 
                  }}>
                    <span>{formatDate(item.createdAt)}</span>
                    <span style={{ color: config.color }}>{config.label}</span>
                  </div>
                </div>
                
                {/* 操作按钮 */}
                <div style={{ display: 'flex', gap: '6px' }} onClick={e => e.stopPropagation()}>
                  {item.status === 'completed' && (
                    <button className="btn btn-success" style={{ padding: '8px 12px' }}
                      onClick={() => navigate(`/note/${item.task_id}`)}>
                      <Eye size={16} />
                      查看
                    </button>
                  )}
                  {item.status === 'failed' && (
                    <button className="btn btn-secondary" style={{ padding: '8px 12px' }}
                      onClick={() => handleRetry(item.task_id)}>
                      <RefreshCw size={16} />
                    </button>
                  )}
                  <button className="btn btn-danger" style={{ padding: '8px' }}
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
