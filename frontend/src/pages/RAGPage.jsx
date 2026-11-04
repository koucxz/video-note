import { useState, useRef, useEffect } from "react"
import { Send, Loader2, Bot, User, FileText, BookOpen } from "lucide-react"
import ReactMarkdown from "react-markdown"
import { ragAsk, getHistoryAll, getCollections } from "../api/client"
import { useLang } from "../context/LangContext"
import { Button } from "../components/ui/button"
import { Card } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Input } from "../components/ui/input"
import { OverflowTooltip } from "../components/OverflowTooltip"
import { cn } from "../lib/utils"

export default function RAGPage() {
  const { t } = useLang()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [notes, setNotes] = useState([])
  const [collections, setCollections] = useState([])
  const [selectedNotes, setSelectedNotes] = useState(new Set())
  const bottomRef = useRef(null)

  useEffect(() => {
    getHistoryAll()
      .then(list => setNotes(list.filter(i => i.status === "completed")))
      .catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const toggleNote = (taskId) => {
    setSelectedNotes(prev => {
      const next = new Set(prev)
      next.has(taskId) ? next.delete(taskId) : next.add(taskId)
      return next
    })
  }

  const handleSend = async () => {
    const q = input.trim()
    if (!q || loading) return
    const userMsg = { role: "user", content: q }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setLoading(true)
    try {
      const scope = selectedNotes.size > 0 ? { task_ids: [...selectedNotes] } : {}
      const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }))
      const resp = await ragAsk(q, history, scope)
      setMessages(prev => [...prev, { role: "assistant", content: resp.answer || t('rag.generateFailed'), sources: resp.sources || [], tokens: resp.tokens || 0 }])
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: t('rag.requestFailed'), error: true }])
    } finally { setLoading(false) }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <div className="hidden w-72 shrink-0 border-r bg-background md:block">
        <div className="sticky top-14 flex h-[calc(100vh-3.5rem)] flex-col p-3">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">{t('rag.knowledgeScope')}</h3>
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setSelectedNotes(new Set(notes.map(n => n.task_id)))}>{t('rag.selectAll')}</Button>
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setSelectedNotes(new Set())}>{t('rag.clear')}</Button>
            </div>
          </div>
          <p className="mb-2 text-xs text-muted-foreground">
            {selectedNotes.size === 0 ? t('rag.searchingAll') : t('rag.selectedCount', { count: selectedNotes.size })}
          </p>
          {collections.length > 0 && (
            <div className="mb-3 space-y-1">
              <p className="text-xs font-medium text-muted-foreground">{t('rag.byCollection')}</p>
              <div className="flex flex-wrap gap-1">
                {collections.map(col => (
                  <Button key={col.id} variant="outline" size="sm" className="h-6 px-2 text-xs" onClick={() => {
                    const ids = (col.noteIds || []).filter(id => notes.some(n => n.task_id === id))
                    setSelectedNotes(prev => { const next = new Set(prev); ids.forEach(id => next.add(id)); return next })
                  }}>{col.name}</Button>
                ))}
              </div>
            </div>
          )}
          <div className="flex-1 space-y-0.5 overflow-y-auto">
            {notes.map(item => (
              <label key={item.task_id} className={cn("flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors", selectedNotes.has(item.task_id) ? "bg-primary/10" : "hover:bg-muted")}>
                <input type="checkbox" checked={selectedNotes.has(item.task_id)} onChange={() => toggleNote(item.task_id)} className="h-3.5 w-3.5 rounded accent-primary" />
                <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <OverflowTooltip className="truncate" text={item.videoName} />
              </label>
            ))}
          </div>
        </div>
      </div>
      <div className="flex flex-1 flex-col">
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <BookOpen className="h-8 w-8 text-primary" />
              </div>
              <h2 className="mb-2 text-lg font-semibold">{t('rag.title')}</h2>
              <p className="max-w-md text-sm text-muted-foreground">
                {selectedNotes.size > 0
                  ? t('rag.basedOnSelected', { count: selectedNotes.size })
                  : t('rag.basedOnAll')}
              </p>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((msg, i) => (
                <div key={i} className={cn("flex gap-3", msg.role === "user" && "justify-end")}>
                  {msg.role !== "user" && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div className={cn("max-w-[80%] rounded-xl px-4 py-3 text-sm", msg.role === "user" ? "bg-primary text-primary-foreground" : msg.error ? "bg-destructive/10 text-destructive" : "bg-muted")}>
                    {msg.role === "user" ? <p className="whitespace-pre-wrap">{msg.content}</p> : (
                      <>
                        <article className="prose prose-sm dark:prose-invert max-w-none">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </article>
                        {msg.sources?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {msg.sources.map((s, j) => (
                              <Badge key={j} variant="outline" className="text-xs">
                                <FileText className="mr-1 h-3 w-3" />{s.title?.substring(0, 30)}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                  {msg.role === "user" && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex items-center gap-2 rounded-xl bg-muted px-4 py-3">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm text-muted-foreground">{t('rag.thinking')}</span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
        <div className="border-t p-4">
          <div className="mx-auto max-w-3xl">
            <div className="flex gap-2">
              <Input value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder={t('rag.placeholder')} disabled={loading} className="flex-1" />
              <Button onClick={handleSend} disabled={loading || !input.trim()}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}