import { useState, useRef, useEffect } from "react"
import { Send, Loader2, Bot, User, FileText, BookOpen, Plus, Pencil, Trash2 } from "lucide-react"
import ReactMarkdown from "react-markdown"
import {
  ragAsk, getHistoryAll, getCollections, getCollectionNotes,
  getRagSessions, createRagSession, getRagSession, renameRagSession, deleteRagSession,
} from "../api/client"
import { useLang } from "../context/LangContext"
import { Button } from "../components/ui/button"
import { Badge } from "../components/ui/badge"
import { Input } from "../components/ui/input"
import { cn } from "../lib/utils"

const NEW_SESSION_TITLE = "新会话"

function ThinkingIndicator({ step, t }) {
  const steps = [
    t('rag.thinkingSearch'),
    t('rag.thinkingContext'),
    t('rag.thinkingAnswer'),
  ]
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="min-w-[220px] rounded-xl border border-primary/10 bg-muted/70 px-4 py-3">
        <div className="mb-2 flex items-center gap-2 text-sm font-medium">
          <span className="flex gap-0.5" aria-hidden="true"><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-.2s]" /><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-.1s]" /><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" /></span>
          <span>{t('rag.thinking')}</span>
        </div>
        <div className="space-y-1 text-xs text-muted-foreground">
          {steps.map((label, index) => <div key={label} className={cn("flex items-center gap-2", index === step && "font-medium text-foreground")}>
            <span className={cn("h-1.5 w-1.5 rounded-full", index < step ? "bg-emerald-500" : index === step ? "animate-pulse bg-primary" : "bg-muted-foreground/30")} />
            <span>{label}</span>
          </div>)}
        </div>
      </div>
    </div>
  )
}

export default function RAGPage() {
  const { t } = useLang()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [notes, setNotes] = useState([])
  const [collections, setCollections] = useState([])
  const [selectedNotes, setSelectedNotes] = useState(new Set())
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  const [thinkingStep, setThinkingStep] = useState(0)
  const [typingId, setTypingId] = useState(null)
  const typingTimer = useRef(null)
  const bottomRef = useRef(null)

  const applySession = (detail) => {
    const scopeIds = detail?.session?.scope?.task_ids || []
    setActiveSessionId(detail.session.id)
    setMessages((detail.messages || []).map(m => ({
      id: m.id, role: m.role, content: m.content, sources: m.sources || [], tokens: m.tokens || 0,
    })))
    setSelectedNotes(new Set(scopeIds))
  }

  const refreshSessions = async (preferredId = null) => {
    const resp = await getRagSessions()
    let list = resp.sessions || []
    if (!list.length) {
      const created = await createRagSession(t('rag.newSession'), { task_ids: [] })
      list = [created]
    }
    setSessions(list)
    const nextId = preferredId || activeSessionId || list[0].id
    const detail = await getRagSession(nextId).catch(() => getRagSession(list[0].id))
    applySession(detail)
  }

  useEffect(() => {
    let cancelled = false
    setSessionLoading(true)
    Promise.all([
      getHistoryAll().then(list => { if (!cancelled) setNotes(list.filter(i => i.status === "completed")) }).catch(() => {}),
      getCollections().then(async resp => {
        const cols = await Promise.all((resp.collections || []).map(async col => {
          const detail = await getCollectionNotes(col.id).catch(() => ({ notes: [] }))
          return { ...col, noteIds: (detail.notes || []).map(item => item.task_id) }
        }))
        if (!cancelled) setCollections(cols)
      }).catch(() => {}),
      refreshSessions().catch(() => {}).finally(() => { if (!cancelled) setSessionLoading(false) }),
    ])
    return () => { cancelled = true }
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

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
    const fullText = message.content || ""
    setMessages(prev => [...prev, { ...message, id, content: "" }])
    setTypingId(id)
    let cursor = 0
    if (typingTimer.current) window.clearInterval(typingTimer.current)
    typingTimer.current = window.setInterval(() => {
      cursor = Math.min(cursor + 1, fullText.length)
      setMessages(prev => prev.map(item => item.id === id ? { ...item, content: fullText.slice(0, cursor) } : item))
      if (cursor >= fullText.length) {
        window.clearInterval(typingTimer.current)
        typingTimer.current = null
        setTypingId(null)
      }
    }, 18)
  }

  const toggleNote = (taskId) => {
    setSelectedNotes(prev => {
      const next = new Set(prev)
      next.has(taskId) ? next.delete(taskId) : next.add(taskId)
      return next
    })
  }

  const handleNewSession = async () => {
    const created = await createRagSession(t('rag.newSession'), { task_ids: [...selectedNotes] })
    setSessions(prev => [created, ...prev])
    applySession({ session: created, messages: [] })
  }

  const handleSelectSession = async (sessionId) => {
    if (sessionId === activeSessionId || sessionLoading) return
    setSessionLoading(true)
    try { applySession(await getRagSession(sessionId)) } catch {} finally { setSessionLoading(false) }
  }

  const handleRenameSession = async (session) => {
    const title = window.prompt(t('rag.renamePrompt'), session.title)
    if (!title || title.trim() === session.title) return
    try {
      const updated = await renameRagSession(session.id, title.trim())
      setSessions(prev => prev.map(item => item.id === updated.id ? { ...item, ...updated } : item))
    } catch {}
  }

  const handleDeleteSession = async (session) => {
    if (!window.confirm(t('rag.confirmDeleteSession'))) return
    try {
      await deleteRagSession(session.id)
      const remaining = sessions.filter(item => item.id !== session.id)
      setSessions(remaining)
      if (session.id === activeSessionId) {
        if (remaining.length) applySession(await getRagSession(remaining[0].id))
        else await refreshSessions()
      }
    } catch {}
  }

  const handleSend = async () => {
    const q = input.trim()
    if (!q || loading || typingId || !activeSessionId) return
    setInput("")
    const localUserMessage = { id: `user-${Date.now()}`, role: "user", content: q }
    setMessages(prev => [...prev, localUserMessage])
    setLoading(true)
    try {
      const scope = { task_ids: [...selectedNotes] }
      const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }))
      const resp = await ragAsk(q, history, scope, activeSessionId)
      const assistantMessage = resp.assistant_message || {
        role: "assistant", content: resp.answer || t('rag.generateFailed'),
        sources: resp.sources || [], tokens: resp.tokens || 0,
      }
      typeAssistantMessage({ ...assistantMessage, id: assistantMessage.id || `assistant-${Date.now()}` })
      setSessions(prev => prev.map(item => item.id === activeSessionId ? {
        ...item, scope, message_count: (item.message_count || 0) + 2,
        preview: assistantMessage.content, updated_at: new Date().toISOString(),
      } : item))
      const current = sessions.find(item => item.id === activeSessionId)
      if (current && (current.title === NEW_SESSION_TITLE || current.message_count === 0)) {
        const updated = await renameRagSession(activeSessionId, q.slice(0, 30))
        setSessions(prev => prev.map(item => item.id === updated.id ? { ...item, ...updated } : item))
      }
    } catch {
      typeAssistantMessage({ role: "assistant", content: t('rag.requestFailed'), error: true })
    } finally { setLoading(false) }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <aside className="hidden w-80 shrink-0 border-r bg-background md:block">
        <div className="sticky top-14 flex h-[calc(100vh-3.5rem)] flex-col p-3">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">{t('rag.sessions')}</h3>
            <Button variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={handleNewSession}><Plus className="mr-1 h-3.5 w-3.5" />{t('rag.newSession')}</Button>
          </div>
          <div className="mb-4 max-h-56 space-y-1 overflow-y-auto">
            {sessionLoading && <p className="px-2 py-2 text-xs text-muted-foreground">{t('common.loading')}</p>}
            {!sessionLoading && sessions.length === 0 && <p className="px-2 py-2 text-xs text-muted-foreground">{t('rag.noSessions')}</p>}
            {sessions.map(session => (
              <div key={session.id} className={cn("group flex items-center gap-1 rounded-md px-2 py-1.5", activeSessionId === session.id ? "bg-primary/10" : "hover:bg-muted")}>
                <button className="min-w-0 flex-1 text-left" onClick={() => handleSelectSession(session.id)}>
                  <div className="truncate text-xs font-medium">{session.title}</div>
                  <div className="truncate text-[10px] text-muted-foreground">{session.preview || t('rag.emptySession')}</div>
                </button>
                <button className="rounded p-1 text-muted-foreground opacity-0 hover:bg-background group-hover:opacity-100" onClick={() => handleRenameSession(session)} aria-label={t('rag.rename')}><Pencil className="h-3 w-3" /></button>
                <button className="rounded p-1 text-muted-foreground opacity-0 hover:bg-background group-hover:opacity-100" onClick={() => handleDeleteSession(session)} aria-label={t('rag.deleteSession')}><Trash2 className="h-3 w-3" /></button>
              </div>
            ))}
          </div>

          <div className="mb-2 flex items-center justify-between border-t pt-3">
            <h3 className="text-sm font-semibold">{t('rag.knowledgeScope')}</h3>
            <div className="flex gap-1"><Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setSelectedNotes(new Set(notes.map(n => n.task_id)))}>{t('rag.selectAll')}</Button><Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setSelectedNotes(new Set())}>{t('rag.clear')}</Button></div>
          </div>
          <p className="mb-2 text-xs text-muted-foreground">{selectedNotes.size === 0 ? t('rag.searchingAll') : t('rag.selectedCount', { count: selectedNotes.size })}</p>
          {collections.length > 0 && <div className="mb-3 space-y-1"><p className="text-xs font-medium text-muted-foreground">{t('rag.byCollection')}</p><div className="flex flex-wrap gap-1">{collections.map(col => <Button key={col.id} variant="outline" size="sm" className="h-6 px-2 text-xs" onClick={() => setSelectedNotes(prev => { const next = new Set(prev); (col.noteIds || []).forEach(id => next.add(id)); return next })}>{col.name}</Button>)}</div></div>}
          <div className="flex-1 space-y-0.5 overflow-y-auto">{notes.map(item => <label key={item.task_id} className={cn("flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors", selectedNotes.has(item.task_id) ? "bg-primary/10" : "hover:bg-muted")}><input type="checkbox" checked={selectedNotes.has(item.task_id)} onChange={() => toggleNote(item.task_id)} className="h-3.5 w-3.5 rounded accent-primary" /><FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" /><span className="truncate">{item.videoName}</span></label>)}</div>
        </div>
      </aside>
      <div className="flex flex-1 flex-col">
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? <div className="flex flex-col items-center justify-center py-24 text-center"><div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10"><BookOpen className="h-8 w-8 text-primary" /></div><h2 className="mb-2 text-lg font-semibold">{t('rag.title')}</h2><p className="max-w-md text-sm text-muted-foreground">{selectedNotes.size > 0 ? t('rag.basedOnSelected', { count: selectedNotes.size }) : t('rag.basedOnAll')}</p></div> : <div className="mx-auto max-w-3xl space-y-4">{messages.map((msg, i) => <div key={msg.id || i} className={cn("flex gap-3", msg.role === "user" && "justify-end")}>{msg.role !== "user" && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10"><Bot className="h-4 w-4 text-primary" /></div>}<div className={cn("max-w-[80%] rounded-xl px-4 py-3 text-sm", msg.role === "user" ? "bg-primary text-primary-foreground" : msg.error ? "bg-destructive/10 text-destructive" : "bg-muted")}>{msg.role === "user" ? <p className="whitespace-pre-wrap">{msg.content}</p> : <><article className="prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown>{msg.content}</ReactMarkdown></article>{msg.sources?.length > 0 && <div className="mt-2 flex flex-wrap gap-1">{msg.sources.map((s, j) => <Badge key={j} variant="outline" className="text-xs"><FileText className="mr-1 h-3 w-3" />{s.title?.substring(0, 30)}</Badge>)}</div>}</>}</div>{msg.role === "user" && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted"><User className="h-4 w-4" /></div>}</div>)}{loading && <ThinkingIndicator step={thinkingStep} t={t} />}<div ref={bottomRef} /></div>}
        </div>
        <div className="border-t p-4"><div className="mx-auto max-w-3xl"><div className="flex gap-2"><Input value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder={t('rag.placeholder')} disabled={loading || typingId || sessionLoading} className="flex-1" /><Button onClick={handleSend} disabled={loading || typingId || sessionLoading || !input.trim()}>{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button></div></div></div>
      </div>
    </div>
  )
}
