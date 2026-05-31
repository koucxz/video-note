import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { History, FileText, Trash2, Eye, RefreshCw, Loader2 } from 'lucide-react'
import { getHistory, deleteTask, retryTask } from '../api/client'

function HistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      setLoading(true)
      const data = await getHistory()
      setHistory(data)
    } catch (err) {
      console.error('加载历史记录失败:', err)
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
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'var(--success)'
      case 'failed': return 'var(--error)'
      case 'processing': return 'var(--primary)'
      default: return 'var(--text-secondary)'
    }
  }

  const getStatusLabel = (status) => {
    switch (status) {
      case 'completed': return '已完成'
      case 'failed': return '失败'
      case 'processing': return '处理中'
      case 'pending': return '等待中'
      default: return status
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '48px' }}>
        <Loader2 size={48} className="animate-spin" color="var(--primary)" />
      </div>
    )
  }

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px'
      }}>
        <h1 style={{ fontSize: '28px', fontWeight: '600' }}>
          <History size={28} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
          历史记录
        </h1>
        <button className="btn btn-secondary" onClick={loadHistory}>
          刷新
        </button>
      </div>

      {history.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px' }}>
          <FileText size={48} color="var(--text-secondary)" />
          <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>
            暂无处理记录
          </p>
          <button
            className="btn btn-primary"
            style={{ marginTop: '16px' }}
            onClick={() => navigate('/')}
          >
            上传第一个视频
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {history.map((item) => (
            <div key={item.task_id} className="card">
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ fontSize: '16px', fontWeight: '500' }}>
                    {item.videoName}
                  </h3>
                  <div style={{
                    display: 'flex',
                    gap: '16px',
                    marginTop: '8px',
                    color: 'var(--text-secondary)',
                    fontSize: '14px'
                  }}>
                    <span>{formatDate(item.createdAt)}</span>
                    <span style={{ color: getStatusColor(item.status) }}>
                      {getStatusLabel(item.status)}
                    </span>
                  </div>
                </div>
                
                <div style={{ display: 'flex', gap: '8px' }}>
                  {item.status === 'completed' && (
                    <button
                      className="btn btn-primary"
                      onClick={() => navigate(`/note/${item.task_id}`)}
                    >
                      <Eye size={16} />
                      查看笔记
                    </button>
                  )}
                  {item.status === 'failed' && (
                    <button
                      className="btn btn-secondary"
                      onClick={() => handleRetry(item.task_id)}
                    >
                      <RefreshCw size={16} />
                      重试
                    </button>
                  )}
                  <button
                    className="btn btn-danger"
                    onClick={() => handleDelete(item.task_id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default HistoryPage
