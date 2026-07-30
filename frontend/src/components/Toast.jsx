import { useState, useEffect } from "react"
import { X, CheckCircle2, AlertTriangle, Info } from "lucide-react"
import { cn } from "../lib/utils"

const ICONS = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
}

const STYLES = {
  success: {
    bg: "bg-emerald-50 dark:bg-emerald-950/50",
    border: "border-emerald-200 dark:border-emerald-800",
    icon: "text-emerald-500",
  },
  error: {
    bg: "bg-red-50 dark:bg-red-950/50",
    border: "border-red-200 dark:border-red-800",
    icon: "text-red-500",
  },
  info: {
    bg: "bg-blue-50 dark:bg-blue-950/50",
    border: "border-blue-200 dark:border-blue-800",
    icon: "text-blue-500",
  },
}

export default function Toast({ toasts, onRemove }) {
  return (
    <div className="fixed inset-x-0 top-0 z-[9999] flex flex-col items-end gap-2 p-4 sm:top-4 sm:right-4 sm:p-0">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onRemove={onRemove} />
      ))}
    </div>
  )
}

function ToastItem({ toast, onRemove }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    requestAnimationFrame(() => setVisible(true))
  }, [])
  useEffect(() => {
    const timer = setTimeout(
      () => {
        setVisible(false)
        setTimeout(() => onRemove(toast.id), 300)
      },
      toast.duration || 4000
    )
    return () => clearTimeout(timer)
  }, [toast.id, toast.duration, onRemove])

  const Icon = ICONS[toast.type] || Info
  const style = STYLES[toast.type] || STYLES.info

  return (
    <div
      className={cn(
        "flex max-w-sm items-start gap-3 rounded-lg border p-3 shadow-lg transition-all duration-300",
        style.bg,
        style.border,
        visible ? "translate-x-0 opacity-100" : "translate-x-full opacity-0"
      )}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", style.icon)} />
      <div className="min-w-0 flex-1">
        {toast.title && (
          <p className="mb-0.5 text-sm font-semibold">{typeof toast.title === "string" ? toast.title : String(toast.title)}</p>
        )}
        <p className="text-xs leading-relaxed text-muted-foreground">
          {typeof toast.message === "object"
            ? JSON.stringify(toast.message)
            : toast.message}
        </p>
      </div>
      <button
        onClick={() => onRemove(toast.id)}
        className="shrink-0 text-muted-foreground hover:text-foreground"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
