import { memo, useState, useRef, useEffect } from "react"
import { Send, Loader2, Bot, User, FileText, BookOpen, Plus, Pencil, Trash2 } from "lucide-react"
import ReactMarkdown from "react-markdown"
import {
  ragAsk, getHistoryAll,
  getRagSessions, getRagSession, renameRagSession, deleteRagSession,
} from "../api/client"
import { useLang } from "../context/LangContext"
import { Button } from "../components/ui/button"
import { Badge } from "../components/ui/badge"
import { Input } from "../components/ui/input"
import { cn } from "../lib/utils"

function ThinkingIndicator({ step, t }) {
  const steps = [
    t("rag.thinkingSearch"),
    t("rag.thinkingContext"),
    t("rag.thinkingAnswer"),
  ]
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="min-w-[220px] rounded-xl border border-primary/10 bg-muted/70 px-4 py-3">
        <div className="mb-1 flex items-center gap-2 text-sm font-medium">
          <span className="flex gap-0.5" aria-hidden="true">
            <i className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-.2s]" />
            <i className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-.1s]" />
            <i className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
          </span>
          <span>{t("rag.thinking")}</span>
        </div>
        <div className="text-xs text-muted-foreground">{steps[step] || steps[0]}</div>
      </div>
    </div>
  )
}

function ThinkingText({ content, done, t }) {
  if (!content) return null
  const lines = String(content)
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map(line => line.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .filter((line, index, items) => index === 0 || line !== items[index - 1])
    .slice(-3)

  return (
    <div className="mb-3 rounded-lg border border-border/70 bg-background/70 px-3 py-2 text-xs text-muted-foreground">
      <div className="mb-1 flex items-center gap-1.5 font-medium text-foreground">
        <span className={cn("h-1.5 w-1.5 rounded-full bg-primary", !done && "animate-pulse")} />
        {t("rag.thinkingProcess")}
      </div>
      <div className="space-y-0.5" aria-live="polite">
        {lines.map((line, index) => (
          <div key={index} className="truncate leading-5" title={line}>{line}</div>
        ))}
      </div>
    </div>
  )
}

// 打字机动效固定总时长：无论回答多长，都只在最多 ~1.3s 内逐段推进，
// 避免「后端已返回，用户还要盯着逐字输出几十秒且输入框被锁死」。
const TYPE_INTERVAL_MS = 18
const MAX_TYPE_TICKS = 70

const MessageRow = memo(function MessageRow({ message, t }) {
  return (
    <div className={cn("flex gap-3", message.role === "user" && "justify-end")}>
      {message.role !== "user" && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10"><Bot className="h-4 w-4 text-primary" /></div>}
      <div className={cn("max-w-[80%] rounded-xl px-4 py-3 text-sm", message.role === "user" ? "bg-primary text-primary-foreground" : message.error ? "bg-destructive/10 text-destructive" : "bg-muted")}>
        {message.role === "user" ? <p className="whitespace-pre-wrap">{message.content}</p> : (
          <>
            <ThinkingText content={message.thinking} done={message.thinking === message.fullThinking} t={t} />
            <article className="prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown>{message.content}</ReactMarkdown></article>
            {message.sources?.length > 0 && <div className="mt-2 flex flex-wrap gap-1">{message.sources.map((source, sourceIndex) => <Badge key={sourceIndex} variant="outline" className="text-xs"><FileText className="mr-1 h-3 w-3" />{source.title?.substring(0, 30)}</Badge>)}</div>}
          </>
        )}
      </div>
      {message.role === "user" && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted"><User className="h-4 w-4" /></div>}
    </div>
  )
})

export default function RAGPage() {
  const { t } = useLang()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [notes, setNotes] = useState([])
  const [selectedNotes, setSelectedNotes] = useState(new Set())
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [thinkingStep, setThinkingStep] = useState(0)
  const [typingId, setTypingId] = useState(null)
  const [sessionError, setSessionError] = useState("")
  const typingTimer = useRef(null)
  const messagesScrollRef = useRef(null)
  const restoreScrollRef = useRef(false)

  const resetDraft = () => {
    restoreScrollRef.current = true
    setActiveSessionId(null)
    setMessages([])
    setSessionError("")
  }

  const applySession = (detail) => {
    if (!detail?.session) return
    restoreScrollRef.current = true
    setActiveSessionId(detail.session.id)
    setMessages((detail.messages || []).map(message => ({
      id: message.id,
      role: message.role,
      content: message.content,
      sources: message.sources || [],
      tokens: message.tokens || 0,
    })))
    setSelectedNotes(new Set(detail.session.scope?.task_ids || []))
    setSessionError("")
  }

  const refreshSessions = async (preferredId = null) => {
    try {
      const response = await getRagSessions()
      const list = response.sessions || []
      setSessions(list)
      const nextId = preferredId || activeSessionId || list[0]?.id
      if (nextId) {
        const detail = await getRagSession(nextId)
        applySession(detail)
      } else {
        resetDraft()
      }
    } catch {
      setSessions([])
      resetDraft()
      setSessionError(t("rag.sessionLoadFailed"))
    }
  }

  useEffect(() => {
    getHistoryAll()
      .then(list => setNotes(list.filter(item => item.status === "completed")))
      .catch(() => {})
    refreshSessions()
  }, [])

  useEffect(() => {
    const container = messagesScrollRef.current
    if (!container) return
    const force = restoreScrollRef.current
    restoreScrollRef.current = false
    // 用户往上翻看历史时不强行拽回底部
    const distance = container.scrollHeight - container.scrollTop - container.clientHeight
    if (!force && distance > 160) return
    // 打字期间 messages 每次变化都会触发这里；用瞬时滚动，避免每秒数十次
    // 重启平滑滚动动画造成掉帧。普通新消息仍保留平滑效果。
    if (force || typingTimer.current) container.scrollTop = container.scrollHeight
    else container.scrollTo({ top: container.scrollHeight, behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (!loading) return undefined
    setThinkingStep(0)
    const timer = window.setInterval(() => setThinkingStep(step => Math.min(step + 1, 2)), 900)
    return () => window.clearInterval(timer)
  }, [loading])

  useEffect(() => () => {
    if (typingTimer.current) window.clearInterval(typingTimer.current)
  }, [])

  const typeAssistantMessage = (message) => {
    const id = message.id || `assistant-${Date.now()}`
    const fullThinking = message.thinking || ""
    const fullAnswer = message.content || ""
    // 按总字数自适应步长，把打字机总时长钉在 MAX_TYPE_TICKS * TYPE_INTERVAL_MS 以内
    const step = Math.max(1, Math.ceil((fullThinking.length + fullAnswer.length) / MAX_TYPE_TICKS))
    setMessages(prev => [...prev, { ...message, id, content: "", thinking: "", fullThinking }])
    setTypingId(id)
    let phase = fullThinking ? "thinking" : "answer"
    let cursor = 0
    if (typingTimer.current) window.clearInterval(typingTimer.current)
    typingTimer.current = window.setInterval(() => {
      const value = phase === "thinking" ? fullThinking : fullAnswer
      cursor = Math.min(cursor + step, value.length)
      const slice = value.slice(0, cursor)
      // 只有正在输出的那一条消息对象会换新引用，其余行由 MessageRow 的 memo 跳过重渲染
      setMessages(prev => prev.map(item => item.id === id
        ? (phase === "thinking" ? { ...item, thinking: slice } : { ...item, content: slice })
        : item))
      if (cursor >= value.length) {
        if (phase === "thinking" && fullAnswer) {
          phase = "answer"
          cursor = 0
        } else {
          window.clearInterval(typingTimer.current)
          typingTimer.current = null
          setTypingId(null)
        }
      }
    }, TYPE_INTERVAL_MS)
  }

  const toggleNote = (taskId) => {
    setSelectedNotes(previous => {
      const next = new Set(previous)
      next.has(taskId) ? next.delete(taskId) : next.add(taskId)
      return next
    })
  }

  const handleNewSession = () => {
    if (typingId || loading) return
    resetDraft()
  }

  const handleSelectSession = async (sessionId) => {
    if (sessionId === activeSessionId || loading || typingId) return
    try {
      applySession(await getRagSession(sessionId))
    } catch {
      setSessionError(t("rag.sessionLoadFailed"))
    }
  }

  const handleRenameSession = async (session) => {
    const title = window.prompt(t("rag.renamePrompt"), session.title)
    const trimmed = title?.trim()
    if (!trimmed || trimmed === session.title) return
    try {
      const updated = await renameRagSession(session.id, trimmed)
      setSessions(previous => previous.map(item => item.id === updated.id ? { ...item, ...updated } : item))
    } catch {
      setSessionError(t("rag.renameFailed"))
    }
  }

  const handleDeleteSession = async (session) => {
    if (!window.confirm(t("rag.confirmDeleteSession"))) return
    try {
      await deleteRagSession(session.id)
      const remaining = sessions.filter(item => item.id !== session.id)
      setSessions(remaining)
      if (session.id === activeSessionId) {
        if (remaining.length) applySession(await getRagSession(remaining[0].id))
        else resetDraft()
      }
    } catch {
      setSessionError(t("rag.deleteFailed"))
    }
  }

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading || typingId) return
    setInput("")
    setSessionError("")
    setMessages(previous => [...previous, { id: `user-${Date.now()}`, role: "user", content: question }])
    setLoading(true)
    try {
      const scope = { task_ids: [...selectedNotes] }
      const history = messages.slice(-6).map(message => ({ role: message.role, content: message.content }))
      const response = await ragAsk(question, history, scope, activeSessionId)
      const sessionId = response.session_id || activeSessionId
      const assistantMessage = response.assistant_message || {
        role: "assistant",
        content: response.answer || t("rag.generateFailed"),
        sources: response.sources || [],
        tokens: response.tokens || 0,
      }
      typeAssistantMessage({
        ...assistantMessage,
        id: assistantMessage.id || `assistant-${Date.now()}`,
        thinking: response.thinking || "",
      })
      if (sessionId) {
        setActiveSessionId(sessionId)
        setSessions(previous => {
          const current = previous.find(item => item.id === sessionId)
          const next = {
            ...(current || {}),
            id: sessionId,
            title: current?.title || question.slice(0, 30),
            scope,
            message_count: (current?.message_count || 0) + 2,
            preview: assistantMessage.content,
            updated_at: new Date().toISOString(),
          }
          return [next, ...previous.filter(item => item.id !== sessionId)]
        })
      }
    } catch {
      typeAssistantMessage({ role: "assistant", content: t("rag.requestFailed"), error: true })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-[calc(100vh-6.5rem)] min-h-0 overflow-hidden">
      <aside className="hidden w-80 min-h-0 shrink-0 border-r bg-background md:block">
        <div className="flex h-full min-h-0 flex-col p-3">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">{t("rag.sessions")}</h3>
            <Button variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={handleNewSession} disabled={loading || !!typingId}>
              <Plus className="mr-1 h-3.5 w-3.5" />{t("rag.newSession")}
            </Button>
          </div>
          {sessionError && <p className="mb-2 px-2 text-xs text-destructive">{sessionError}</p>}
          <div className="mb-4 max-h-56 space-y-1 overflow-y-auto">
            {!sessions.length && <p className="px-2 py-2 text-xs text-muted-foreground">{t("rag.noSessions")}</p>}
            {sessions.map(session => (
              <div key={session.id} className={cn("group flex items-center gap-1 rounded-md px-2 py-1.5", activeSessionId === session.id ? "bg-primary/10" : "hover:bg-muted")}>
                <button className="min-w-0 flex-1 text-left" onClick={() => handleSelectSession(session.id)}>
                  <div className="truncate text-xs font-medium">{session.title}</div>
                  <div className="truncate text-[10px] text-muted-foreground">{session.preview || t("rag.emptySession")}</div>
                </button>
                <button className="rounded p-1 text-muted-foreground opacity-0 hover:bg-background group-hover:opacity-100" onClick={() => handleRenameSession(session)} aria-label={t("rag.rename")}>
                  <Pencil className="h-3 w-3" />
                </button>
                <button className="rounded p-1 text-muted-foreground opacity-0 hover:bg-background group-hover:opacity-100" onClick={() => handleDeleteSession(session)} aria-label={t("rag.deleteSession")}>
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>

          <div className="mb-2 flex items-center justify-between border-t pt-3">
            <h3 className="text-sm font-semibold">{t("rag.knowledgeScope")}</h3>
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setSelectedNotes(new Set(notes.map(note => note.task_id)))}>{t("rag.selectAll")}</Button>
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setSelectedNotes(new Set())}>{t("rag.clear")}</Button>
            </div>
          </div>
          <p className="mb-2 text-xs text-muted-foreground">{selectedNotes.size === 0 ? t("rag.searchingAll") : t("rag.selectedCount", { count: selectedNotes.size })}</p>
          <div className="flex-1 space-y-0.5 overflow-y-auto">
            {notes.map(note => (
              <label key={note.task_id} className={cn("flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors", selectedNotes.has(note.task_id) ? "bg-primary/10" : "hover:bg-muted")}>
                <input type="checkbox" checked={selectedNotes.has(note.task_id)} onChange={() => toggleNote(note.task_id)} className="h-3.5 w-3.5 rounded accent-primary" />
                <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{note.videoName}</span>
              </label>
            ))}
          </div>
        </div>
      </aside>

      <div className="flex min-h-0 flex-1 flex-col">
        <div ref={messagesScrollRef} className="min-h-0 flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10"><BookOpen className="h-8 w-8 text-primary" /></div>
              <h2 className="mb-2 text-lg font-semibold">{t("rag.title")}</h2>
              <p className="max-w-md text-sm text-muted-foreground">{selectedNotes.size > 0 ? t("rag.basedOnSelected", { count: selectedNotes.size }) : t("rag.basedOnAll")}</p>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((message, index) => (
                <MessageRow key={message.id || index} message={message} t={t} />
              ))}
              {loading && <ThinkingIndicator step={thinkingStep} t={t} />}
              <div aria-hidden="true" />
            </div>
          )}
        </div>
        <div className="shrink-0 border-t p-4">
          <div className="mx-auto max-w-3xl">
            <div className="flex gap-2">
              <Input value={input} onChange={event => setInput(event.target.value)} onKeyDown={handleKeyDown} placeholder={t("rag.placeholder")} disabled={loading || !!typingId} className="flex-1" />
              <Button onClick={handleSend} disabled={loading || !!typingId || !input.trim()}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
