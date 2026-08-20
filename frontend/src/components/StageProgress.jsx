import { CheckCircle2, Loader2, XCircle } from "lucide-react"
import { useLang } from "../context/LangContext"
import { cn } from "../lib/utils"

function StageProgress({ currentStage, status }) {
  const { t } = useLang()
  const STAGES = [
    { key: "extracting_audio", label: t('processing.stage.extracting_audio') },
    { key: "transcribing", label: t('processing.stage.transcribing') },
    { key: "generating_outline", label: t('processing.stage.generating_outline') },
    { key: "extracting_keyframes", label: t('processing.stage.extracting_keyframes') },
    { key: "analyzing_content", label: t('processing.stage.analyzing_content') },
    { key: "generating_note", label: t('processing.stage.generating_note') },
    { key: "completed", label: t('processing.stage.completed') },
  ]
  const idx = STAGES.findIndex((s) => s.key === currentStage)
  const fail = status === "failed"
  const done = status === "completed"

  return (
    <div className="flex items-center justify-between">
      {STAGES.map((s, i) => {
        const isDone = done || i < idx
        const isNow = !done && !fail && i === idx
        const isFail = fail && i === idx
        const isLast = i === STAGES.length - 1

        return (
          <div key={s.key} className="flex flex-1 items-center">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-medium transition-colors",
                  isDone && "border-primary bg-primary text-primary-foreground",
                  isNow && "border-primary bg-primary/10 text-primary",
                  isFail && "border-destructive bg-destructive/10 text-destructive",
                  !isDone && !isNow && !isFail && "border-muted bg-background text-muted-foreground"
                )}
              >
                {isDone ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : isNow ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : isFail ? (
                  <XCircle className="h-4 w-4" />
                ) : (
                  <span>{i + 1}</span>
                )}
              </div>
              <span
                className={cn(
                  "mt-1.5 text-center text-[10px] leading-tight",
                  isNow ? "font-medium text-primary" : "text-muted-foreground"
                )}
              >
                {s.label}
              </span>
            </div>
            {!isLast && (
              <div
                className={cn(
                  "mx-1 mb-5 h-0.5 flex-1 rounded-full transition-colors",
                  isDone ? "bg-primary" : "bg-muted"
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default StageProgress
