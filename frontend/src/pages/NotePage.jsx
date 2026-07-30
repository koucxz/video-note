import { useState, useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  Download, Loader2, Copy, Check, CheckCircle2, FileText, Search, Pencil,
  Sparkles, Save, X, Brain, History, RotateCcw, Trash2,
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import { downloadNotePdf, downloadNoteWord, downloadNoteHtml, getHistoryAll } from "../api/client"
import { useNoteStore } from "../stores/noteStore"
import { useLang } from "../context/LangContext"

import { Button } from "../components/ui/button"
import { Card, CardContent } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Input } from "../components/ui/input"
import { Label } from "../components/ui/label"
import { Separator } from "../components/ui/separator"
import { Skeleton } from "../components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../components/ui/tooltip"
import { cn } from "../lib/utils"

function NotePage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const {
    note, versions, loading, editMode, editContent, editSaving,
    polishing, showVersions, showPolish,
    loadNote, startEdit, cancelEdit, saveEdit, polishNote,
    revertVersion, deleteVersion, toggle,
  } = useNoteStore()
  const [polishExtra, setPolishExtra] = useState("")
  const [copied, setCopied] = useState(false)
  const [notes, setNotes] = useState([])
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const debounceTimer = useRef(null)

  useEffect(() => {
    getHistoryAll().then(list => setNotes(list.filter(i => i.status === "completed"))).catch(() => {})
  }, [])

  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => setDebouncedSearch(search), 300)
    return () => { if (debounceTimer.current) clearTimeout(debounceTimer.current) }
  }, [search])

  useEffect(() => { loadNote(taskId) }, [taskId])

  const handleSaveEdit = async () => {
    try { await saveEdit(taskId) }
    catch { alert(lang === "zh" ? "\u4fdd\u5b58\u5931\u8d25" : "Save failed") }
  }

  const handlePolish = async (style) => {
    try { await polishNote(taskId, style, polishExtra); setPolishExtra("") }
    catch { console.error("Polish failed") }
  }

  const handleRevert = async (verId) => {
    try { await revertVersion(taskId, verId) }
    catch { alert(lang === "zh" ? "\u56de\u6eda\u5931\u8d25" : "Revert failed") }
  }

  const handleDeleteVersion = async (verId) => {
    if (!confirm(lang === "zh" ? "\u786e\u5b9a\u5220\u9664\u6b64\u7248\u672c\uff1f" : "Delete this version?")) return
    try { await deleteVersion(taskId, verId) }
    catch { alert(lang === "zh" ? "\u5220\u9664\u5931\u8d25" : "Delete failed") }
  }

  const handleCopy = () => {
    if (!note) return
    navigator.clipboard.writeText(note.content)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    if (!note) return
    const blob = new Blob([note.content], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a"); a.href = url
    a.download = `${note.filename?.replace(/\.[^.]+$/, "") || "note"}.md`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const filtered = notes.filter(h => !debouncedSearch || h.videoName?.toLowerCase().includes(debouncedSearch.toLowerCase()))

  return (
    <TooltipProvider>
      <div className="flex min-h-[calc(100vh-3.5rem)]">
        {/* Sidebar */}
        <div className="hidden w-64 shrink-0 border-r bg-background md:block">
          <div className="sticky top-14 flex h-[calc(100vh-3.5rem)] flex-col p-3">
            <h3 className="mb-2 px-1 text-sm font-semibold">{t.history} <span className="font-normal text-muted-foreground">({filtered.length})</span></h3>
            <div className="relative mb-2">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder={lang === "zh" ? "\u641c\u7d22..." : "Search..."} value={search} onChange={e => setSearch(e.target.value)} className="h-8 pl-8 text-xs" />
            </div>
            <div className="flex-1 space-y-1 overflow-y-auto">
              {filtered.slice(0, 50).map(item => (
                <button key={item.task_id} onClick={() => navigate(`/note/${item.task_id}`)}
                  className={cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors",
                    item.task_id === taskId ? "bg-primary/10 font-medium text-primary" : "hover:bg-muted")}>
                  <CheckCircle2 className={cn("h-3.5 w-3.5 shrink-0", item.task_id === taskId ? "text-primary" : "text-emerald-500")} />
                  <span className="truncate">{item.videoName}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Main */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6">
            {note && (
              <div className="mb-4 flex flex-wrap items-center justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => toggle("showVersions")}>
                  <History className="mr-1.5 h-4 w-4" />{lang === "zh" ? `\u7248\u672c (${versions.length})` : `Versions (${versions.length})`}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => navigate("/flashcards/" + note.task_id)}><Brain className="mr-1.5 h-4 w-4" />{lang === "zh" ? "\u95ea\u5361" : "Cards"}</Button>
                <Button variant="ghost" size="sm" onClick={startEdit}><Pencil className="mr-1.5 h-4 w-4" />{lang === "zh" ? "\u7f16\u8f91" : "Edit"}</Button>
                <Button variant="ghost" size="sm" onClick={() => toggle("showPolish")} disabled={polishing}>{polishing ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Sparkles className="mr-1.5 h-4 w-4" />}{lang === "zh" ? "\u6da6\u8272" : "Polish"}</Button>
                <Separator orientation="vertical" className="mx-1 h-6" />
                <Button variant="outline" size="sm" onClick={handleCopy}>{copied ? <Check className="mr-1.5 h-4 w-4" /> : <Copy className="mr-1.5 h-4 w-4" />}{copied ? t.copied : t.copy}</Button>
                <Button variant="ghost" size="sm" onClick={() => downloadNoteWord(note.task_id)}><FileText className="mr-1.5 h-4 w-4" />Word</Button>
                <Button variant="ghost" size="sm" onClick={() => downloadNotePdf(note.task_id)}><FileText className="mr-1.5 h-4 w-4" />PDF</Button>
                <Button size="sm" onClick={handleDownload}><Download className="mr-1.5 h-4 w-4" />MD</Button>
                <Button variant="ghost" size="sm" onClick={() => downloadNoteHtml(note.task_id)}><FileText className="mr-1.5 h-4 w-4" />HTML</Button>
              </div>
            )}

            {showVersions && versions.length > 0 && (
              <Card className="mb-4"><CardContent className="p-4">
                <h4 className="mb-3 text-sm font-semibold">{lang === "zh" ? "\u7248\u672c\u5386\u53f2" : "Version History"}</h4>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {[...versions].reverse().map((v, i) => (
                    <div key={v.id} className="flex items-center justify-between rounded-lg border p-2 text-xs">
                      <div>
                        <span className="font-medium">v{v.version_num}</span>
                        <Badge variant="outline" className="ml-2">{v.source}</Badge>
                        <span className="ml-2 text-muted-foreground">{new Date(v.created_at).toLocaleString()}</span>
                      </div>
                      <div className="flex gap-1">
                        {i > 0 && <Button variant="ghost" size="sm" className="h-6 px-2" onClick={() => handleRevert(v.id)}><RotateCcw className="h-3 w-3" /></Button>}
                        {versions.length > 1 && <Button variant="ghost" size="sm" className="h-6 px-2 text-destructive" onClick={() => handleDeleteVersion(v.id)}><Trash2 className="h-3 w-3" /></Button>}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent></Card>
            )}

            {showPolish && (
              <Card className="mb-4"><CardContent className="space-y-3 p-4">
                <Label className="text-sm font-semibold">{lang === "zh" ? "\u9009\u62e9\u6da6\u8272\u98ce\u683c" : "Select polish style"}</Label>
                <div className="flex flex-wrap gap-2">
                  {[["standard", lang === "zh" ? "\u6807\u51c6" : "Standard"], ["summary", lang === "zh" ? "\u7cbe\u7b80" : "Brief"], ["academic", lang === "zh" ? "\u5b66\u672f" : "Academic"], ["creative", lang === "zh" ? "\u521b\u610f" : "Creative"]].map(([id, label]) => (
                    <Button key={id} variant="outline" size="sm" onClick={() => handlePolish(id)} disabled={polishing}>{label}</Button>
                  ))}
                </div>
                <Input value={polishExtra} onChange={e => setPolishExtra(e.target.value)} placeholder={lang === "zh" ? "\u989d\u5916\u8981\u6c42\uff08\u53ef\u9009\uff09" : "Extra instructions (optional)"} className="text-sm" />
              </CardContent></Card>
            )}

            {loading ? (
              <div className="space-y-3 py-12"><Skeleton className="h-8 w-2/3" /><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-5/6" /></div>
            ) : !note ? (
              <div className="flex flex-col items-center justify-center py-24"><FileText className="mb-3 h-12 w-12 text-muted-foreground/50" /><p className="text-muted-foreground">{t.noNote}</p></div>
            ) : (
              <>
                <p className="mb-3 text-xs text-muted-foreground">{note.filename}</p>
                <Card><CardContent className="p-6 md:p-8">
                  {editMode ? (
                    <div className="space-y-3">
                      <div className="flex gap-2">
                        <Button size="sm" onClick={handleSaveEdit} disabled={editSaving}>{editSaving ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Save className="mr-1.5 h-4 w-4" />}{lang === "zh" ? "\u4fdd\u5b58\u4e3a\u65b0\u7248\u672c" : "Save as new version"}</Button>
                        <Button variant="ghost" size="sm" onClick={cancelEdit}><X className="mr-1.5 h-4 w-4" />{lang === "zh" ? "\u53d6\u6d88" : "Cancel"}</Button>
                      </div>
                      <textarea value={editContent} onChange={e => useNoteStore.setState({ editContent: e.target.value })} className="min-h-[400px] w-full rounded-lg border bg-background p-4 font-mono text-sm leading-relaxed outline-none focus:ring-1 focus:ring-ring" />
                    </div>
                  ) : (
                    <article className="prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown>{note.content}</ReactMarkdown></article>
                  )}
                </CardContent></Card>
              </>
            )}
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

export default NotePage
