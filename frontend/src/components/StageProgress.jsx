import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { useLang } from '../context/LangContext'

function StageProgress({ currentStage, status }) {
  const { t } = useLang()
  const STAGES = [
    { key:'extracting_audio', label:t.extractAudio },
    { key:'transcribing', label:t.transcribe },
    { key:'generating_outline', label:t.genOutline },
    { key:'extracting_keyframes', label:t.extractFrames },
    { key:'analyzing_content', label:t.analyzeContent },
    { key:'generating_note', label:t.genNote },
    { key:'completed', label:t.done },
  ]
  const idx = STAGES.findIndex(s=>s.key===currentStage)
  const fail = status==='failed'
  const done = status==='completed'

  return (
    <div className="steps">
      {STAGES.map((s,i) => {
        const isDone = done || i<idx
        const isNow = !done && !fail && i===idx
        const isFail = fail && i===idx
        const last = i===STAGES.length-1

        return (
          <div key={s.key} className="step">
            {!last && <div className={`step-line ${isDone?'done':''}`}/>}
            <div className="step-dot" style={{
              background: isDone?'var(--blue)':isNow?'var(--blue-light)':'var(--white)',
              border: isDone?'none':isNow?'2px solid var(--blue)':isFail?'2px solid var(--red)':'2px solid var(--gray-200)',
              color: isDone?'white':isNow?'var(--blue)':isFail?'var(--red)':'var(--gray-400)',
            }}>
              {isDone ? <CheckCircle2 size={14}/> : isNow ? <Loader2 size={14} className="spin"/> : isFail ? <XCircle size={14}/> : <span>{i+1}</span>}
            </div>
            <div className={`step-text ${isNow?'now':''}`}>{s.label}</div>
          </div>
        )
      })}
    </div>
  )
}

export default StageProgress
