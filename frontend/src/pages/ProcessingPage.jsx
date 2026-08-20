import { useState, useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  Loader2,
  RefreshCw,
  ArrowLeft,
  Wifi,
  AlertTriangle,
  FileQuestion,
  Scissors,
} from "lucide-react"
import { getTaskStatus, retryTask, cancelTask } from "../api/client"
import { useTaskWebSocket } from "../hooks/useWebSocket"
import StageProgress from "../components/StageProgress"
import { useLang } from "../context/LangContext"

import { Button } from "../components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Separator } from "../components/ui/separator"
import { cn } from "../lib/utils"

const ERROR_KIND_ICONS = {
  network: Wifi,
  api: AlertTriangle,
  ffmpeg: Scissors,
  format: FileQuestion,
  interrupted: RefreshCw,
  unknown: AlertTriangle,
}

function ProcessingPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { t } = useLang()
  const [status, setStatus] = useState(null)
  const wsStatus = useTaskWebSocket(taskId)
  const [retryCount, setRetryCount] = useState(0)
  const maxRetries = 3
  const retryingRef = useRef(false)

  useEffect(() => {
    if (wsStatus && wsStatus.status) {
      setStatus((prev) => ({ ...prev, ...wsStatus }))
      if (wsStatus.status === "completed") {
        setTimeout(() => navigate(`/note/${taskId}`), 2000)
      }
    }
  }, [wsStatus, taskId, navigate])

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const data = await getTaskStatus(taskId)
        setStatus(data)
        if (data.status === "completed") {
          clearInterval(timer)
          setTimeout(() => navigate(`/note/${taskId}`), 2000)
        } else if (data.status === "failed") {
          clearInterval(timer)
          if (
            data.error_kind !== "interrupted" &&
            retryCount < maxRetries &&
            !retryingRef.current
          ) {
            retryingRef.current = true
            setRetryCount((prev) => prev + 1)
            setTimeout(async () => {
              try {
                await retryTask(taskId)
                retryingRef.current = false
                window.location.reload()
              } catch (err) {
                retryingRef.current = false
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

  const handleCancel = async () => {
    try {
      await cancelTask(taskId)
      navigate("/history")
    } catch (err) {
      alert(t('processing.cancelFailed'))
    }
  }

  const handleManualRetry = async () => {
    try {
      await retryTask(taskId)
      setRetryCount(0)
      window.location.reload()
    } catch (err) {
      alert(t('processing.retryFailed'))
    }
  }

  if (!status) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  const isCompleted = status.status === "completed"
  const isFailed = status.status === "failed"
  const isAutoRetrying =
    isFailed && retryCount < maxRetries && retryCount > 0
  const errorInfo = {}
  const errorKind = status.error_kind || "unknown"
  const errorKey = ERROR_KIND_ICONS[errorKind] ? errorKind : 'unknown'
  errorInfo.icon = ERROR_KIND_ICONS[errorKey]
  errorInfo.title = t(`processing.error.${errorKey}`)
  errorInfo.hint = t(`processing.error.${errorKey}Hint`)

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => navigate("/history")}>
        <ArrowLeft className="mr-1.5 h-4 w-4" />
        {t('common.back')}
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="break-all text-lg">
            {status.filename}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {isCompleted
              ? t('processing.complete')
              : isFailed
              ? isAutoRetrying
                ? `${t('processing.autoRetry')} (${retryCount}/${maxRetries})`
                : errorInfo.title
              : t('processing.processingWait')}
          </p>
        </CardHeader>
        <CardContent>
          <StageProgress
            currentStage={status.stage}
            status={status.status}
          />
        </CardContent>
      </Card>

      <Card
        className={cn(
          isCompleted && "border-emerald-500/50 bg-emerald-500/5",
          isFailed && !isAutoRetrying && "border-destructive/50 bg-destructive/5",
          isAutoRetrying && "border-primary/50 bg-primary/5",
          !isCompleted && !isFailed && "border-primary/50 bg-primary/5"
        )}
      >
        <CardContent className="flex flex-col items-center justify-center p-8">
          {isCompleted ? (
            <>
              <div className="mb-2 text-4xl">🎉</div>
              <p className="font-semibold text-emerald-600">
                {t('processing.processComplete')}
              </p>
            </>
          ) : isFailed ? (
            isAutoRetrying ? (
              <>
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="mt-3 font-medium text-primary">
                  {t('processing.autoRetry')} ({retryCount}/{maxRetries})
                </p>
              </>
            ) : (
              <>
                <ErrorIcon className="mb-2 h-10 w-10 text-destructive" />
                <p className="mb-1 text-base font-semibold text-destructive">
                  {errorInfo.title}
                </p>
                <p className="mb-4 text-sm text-muted-foreground">
                  {errorInfo.hint}
                </p>
                {status.error && (
                  <details className="mb-4 w-full max-w-md text-xs text-muted-foreground">
                    <summary className="cursor-pointer">
                      {t('processing.technicalDetails')}
                    </summary>
                    <pre className="mt-2 max-h-32 overflow-auto rounded-md bg-muted p-3 text-xs">
                      {status.error}
                    </pre>
                  </details>
                )}
                <Button onClick={handleManualRetry}>
                  <RefreshCw className="mr-1.5 h-4 w-4" />
                  {t('common.retry')}
                </Button>
              </>
            )
          ) : (
            <>
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <Button
                variant="ghost"
                size="sm"
                className="mt-4"
                onClick={handleCancel}
              >
                {t('common.cancel')}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default ProcessingPage


