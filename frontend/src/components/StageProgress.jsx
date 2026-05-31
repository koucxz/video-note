import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

const STAGES = [
  { key: 'extracting_audio', label: '提取音频', icon: '🎵' },
  { key: 'transcribing', label: '语音识别', icon: '🎤' },
  { key: 'generating_outline', label: '生成大纲', icon: '📝' },
  { key: 'extracting_keyframes', label: '提取关键帧', icon: '🖼️' },
  { key: 'analyzing_content', label: '分析内容', icon: '🔍' },
  { key: 'generating_note', label: '生成笔记', icon: '📄' },
  { key: 'completed', label: '完成', icon: '✅' },
]

function StageProgress({ currentStage, status }) {
  const currentIndex = STAGES.findIndex(s => s.key === currentStage)
  const isFailed = status === 'failed'
  const isCompleted = status === 'completed'
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {STAGES.map((stage, index) => {
        const isDone = isCompleted || index < currentIndex
        const isCurrent = !isCompleted && !isFailed && index === currentIndex
        const isFailedStage = isFailed && index === currentIndex
        
        return (
          <div key={stage.key} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* 连接线 */}
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              width: 32
            }}>
              {/* 状态图标 */}
              <div style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: isDone ? 'var(--success-light)' : 
                           isCurrent ? 'var(--primary-light)' : 
                           isFailedStage ? 'var(--error-light)' : 'var(--bg)',
                border: isDone ? '2px solid var(--success)' : 
                        isCurrent ? '2px solid var(--primary)' : 
                        isFailedStage ? '2px solid var(--error)' : '2px solid var(--border)',
                fontSize: '14px',
                flexShrink: 0
              }}>
                {isDone ? <CheckCircle2 size={18} color="var(--success)" /> :
                 isCurrent ? <Loader2 size={18} color="var(--primary)" className="animate-spin" /> :
                 isFailedStage ? <XCircle size={18} color="var(--error)" /> :
                 <span style={{ opacity: 0.4 }}>{stage.icon}</span>}
              </div>
              
              {/* 竖线 */}
              {index < STAGES.length - 1 && (
                <div style={{
                  width: 2,
                  height: 24,
                  background: isDone ? 'var(--success)' : 'var(--border)',
                  transition: 'background 0.3s'
                }} />
              )}
            </div>
            
            {/* 标签 */}
            <div style={{
              flex: 1,
              padding: '8px 0',
              fontWeight: isCurrent ? '600' : '400',
              color: isDone ? 'var(--success)' : 
                     isCurrent ? 'var(--text)' : 
                     isFailedStage ? 'var(--error)' : 'var(--text-secondary)',
              fontSize: isCurrent ? '15px' : '14px'
            }}>
              {stage.label}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default StageProgress
