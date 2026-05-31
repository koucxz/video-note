import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { useLang } from '../context/LangContext'

const STAGES_ZH = [
  { key: 'extracting_audio', label: '提取音频' },
  { key: 'transcribing', label: '语音识别' },
  { key: 'generating_outline', label: '生成大纲' },
  { key: 'extracting_keyframes', label: '提取关键帧' },
  { key: 'analyzing_content', label: '分析内容' },
  { key: 'generating_note', label: '生成笔记' },
  { key: 'completed', label: '完成' },
]

const STAGES_EN = [
  { key: 'extracting_audio', label: 'Audio' },
  { key: 'transcribing', label: 'Transcribe' },
  { key: 'generating_outline', label: 'Outline' },
  { key: 'extracting_keyframes', label: 'Frames' },
  { key: 'analyzing_content', label: 'Analyze' },
  { key: 'generating_note', label: 'Note' },
  { key: 'completed', label: 'Done' },
]

function StageProgress({ currentStage, status }) {
  const { lang } = useLang()
  const STAGES = lang === 'zh' ? STAGES_ZH : STAGES_EN
  const currentIndex = STAGES.findIndex(s => s.key === currentStage)
  const isFailed = status === 'failed'
  const isCompleted = status === 'completed'
  
  return (
    <div className="progress-bar-container">
      {STAGES.map((stage, index) => {
        const isDone = isCompleted || index < currentIndex
        const isCurrent = !isCompleted && !isFailed && index === currentIndex
        const isFailedStage = isFailed && index === currentIndex
        const isLast = index === STAGES.length - 1
        
        return (
          <div key={stage.key} className="progress-step">
            {/* 连接线 */}
            {!isLast && (
              <div className={`progress-line ${isDone ? 'done' : ''}`} />
            )}
            
            {/* 圆点 */}
            <div className="progress-dot" style={{
              background: isDone ? 'var(--primary)' : 
                         isCurrent ? 'var(--primary-50)' : 'var(--card-bg)',
              border: isDone ? 'none' : 
                     isCurrent ? '2px solid var(--primary)' : 
                     isFailedStage ? '2px solid var(--error)' : '2px solid var(--border)',
              color: isDone ? 'white' : 
                     isCurrent ? 'var(--primary)' : 
                     isFailedStage ? 'var(--error)' : 'var(--text-muted)',
            }}>
              {isDone ? <CheckCircle2 size={16} /> :
               isCurrent ? <Loader2 size={16} className="animate-spin" /> :
               isFailedStage ? <XCircle size={16} /> :
               <span>{index + 1}</span>}
            </div>
            
            {/* 标签 */}
            <div className={`progress-label ${isCurrent ? 'active' : ''}`}>
              {stage.label}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default StageProgress
