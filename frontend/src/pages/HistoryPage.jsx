import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import {
  Trash2, RefreshCw, Loader2, Clock, CheckCircle2, XCircle,
  Search, Download, CheckSquare, Square,
  MoreVertical, ExternalLink, Eye, RotateCcw, Pause, Play, Pencil, Activity,
} from "lucide-react"
import { downloadNoteMd, downloadNotePdf, downloadNotesZip, getTaskStatus } from "../api/client"
import { useTaskStore } from "../stores/taskStore"
import { useLang } from "../context/LangContext"
import { useGlobalWebSocket } from "../hooks/useWebSocket"

import { Button } from "../components/ui/button"
import { Card, CardContent } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import { Input } from "../components/ui/input"
import { Progress } from "../components/ui/progress"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "../components/ui/dropdown-menu"
import { Tooltip, TooltipProvider, TooltipTrigger, TooltipContent } from "../components/ui/tooltip"
import { cn } from "../lib/utils"

const statusConfig = {
  completed: { icon: CheckCircle2, variant: "success", color: "text-emerald-500", bg: "bg-emerald-500/10" },
  failed: { icon: XCircle, variant: "destructive", color: "text-destructive", bg: "bg-destructive/10" },
  processing: { icon: Loader2, variant: "default", color: "text-primary", bg: "bg-primary/10" },
  pending: { icon: Clock, variant: "secondary", color: "text-muted-foreground", bg: "bg-muted" },
  paused: { icon: Pause, variant: "secondary", color: "text-amber-500", bg: "bg-amber-500/10" },
}

// 与后端 ProcessingStage 的顺序一致（ASR 关闭时后端会跳过 transcribing）
const STAGE_ORDER = [
  "extracting_audio", "extracting_subtitles", "transcribing",
  "generating_outline", "extracting_keyframes", "analyzing_content", "generating_note",
]

function HistoryPage() {
  const {
    tasks, loading, page, totalPages, total, statusFilter, search, selected,
    setFilter, toggleSelect, selectAll, clearSelection, fetchTasks,
    retryTask, deleteTask, deleteSelected, pauseTask, resumeTask, renameTask, filteredTasks,
    patchTask,
  } = useTaskStore()
  const [downloadFormat, setDownloadFormat] = useState("md")
  const [downloading, setDownloading] = useState(false)
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const debounceRef = useRef(null)
  const wsUpdates = useGlobalWebSocket()

  useEffect(() => { fetchTasks(1) }, [])

  useEffect(() => {
    if (!wsUpdates?.length) return
    const latest = wsUpdates[wsUpdates.length - 1]
    if (!latest?.task_id) return
    patchTask(latest.task_id, { status: latest.status, progress: latest.progress, stage: latest.stage })
    if (latest.status === "completed" || latest.status === "failed") fetchTasks()
  }, [wsUpdates])

  /* 进行中任务的进展详情：打开后每 3 秒拉一次最新状态（WS 掉线也能跟上） */
  const [detail, setDetail] = useState(null)
  const [live, setLive] = useState(null)

  useEffect(() => {
    if (!detail?.task_id) { setLive(null); return }
    let stopped = false
    const pull = async () => {
      try {
        const s = await getTaskStatus(detail.task_id)
        if (stopped) return
        setLive(s)
        patchTask(detail.task_id, { status: s.status, progress: s.progress, stage: s.stage })
        if (s.status === "completed" || s.status === "failed") fetchTasks()
      } catch { /* 网络抖动就保留上一帧，不打断阅读 */ }
    }
    pull()
    const timer = setInterval(pull, 3000)
    return () => { stopped = true; clearInterval(timer) }
  }, [detail?.task_id])

  const stageLabel = (stage) => {
    if (!stage) return "-"
    const key = `processing.stage.${stage}`
    const label = t(key)
    if (label !== key) return label
    if (stage === "queued") return t('history.stageQueued')
    return stage
  }

  const elapsedText = (item) => {
    if (!item?.createdAt) return "-"
    const start = new Date(item.createdAt).getTime()
    if (isNaN(start)) return "-"
    const finished = item.status === "completed" || item.status === "failed"
    const end = finished ? new Date(item.completed_at || Date.now()).getTime() : Date.now()
    const sec = Math.max(0, Math.round((end - start) / 1000))
    const m = Math.floor(sec / 60), s = sec % 60
    return lang === "zh" ? (m ? `${m} 分 ${String(s).padStart(2, "0")} 秒` : `${s} 秒`) : (m ? `${m}m ${s}s` : `${s}s`)
  }

  const handleSearch = (val) => {
    setFilter("search", val)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchTasks(1), 300)
  }

  const handleDelete = async (e, taskId) => {
    e.stopPropagation()
    if (!confirm(t('history.confirmDeleteRecord'))) return
    try { await deleteTask(taskId) } catch { alert(t('common.deleteFailed')) }
  }

  const handleRetry = async (e, taskId) => {
    e.stopPropagation()
    try { await retryTask(taskId) } catch { alert(t('common.retryFailed')) }
  }

  const handlePauseResume = async (e, task) => {
    e.stopPropagation()
    try {
      if (task.status === "paused") await resumeTask(task.task_id)
      else await pauseTask(task.task_id)
    } catch { /* ignore */ }
  }

  const handleRename = async (e, task) => {
    e?.stopPropagation()
    const name = window.prompt(t('history.renamePrompt'), task.videoName || '')
    const trimmed = name?.trim()
    if (!trimmed || trimmed === task.videoName) return
    try { await renameTask(task.task_id, trimmed) } catch { alert(t('history.renameFailed')) }
  }

  const handleBatchZip = async () => {
    if (!selected.size) return
    setDownloading(true)
    try { await downloadNotesZip([...selected], downloadFormat) }
    catch { alert("Download failed") }
    finally { setDownloading(false) }
  }

  const formatDate = (d) => {
    if (!d) return ""
    const dt = new Date(d)
    if (isNaN(dt)) return "-"
    return dt.toLocaleString(lang === "zh" ? "zh-CN" : "en-US", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false })
  }

  const filtered = filteredTasks()

  if (loading && !tasks.length) return (
    <div className="flex items-center justify-center py-24">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  )

  const filterButtons = [
    ["all", t('common.all'), total],
    ["completed", t('status.completed'), tasks.filter(h => h.status === "completed").length],
    ["processing", t('status.processing'), tasks.filter(h => h.status === "processing").length],
    ["failed", t('status.failed'), tasks.filter(h => h.status === "failed").length],
    ["pending", t('status.pending'), tasks.filter(h => h.status === "pending").length],
    ["paused", t('status.paused'), tasks.filter(h => h.status === "paused").length],
  ]

  return (
    <TooltipProvider>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-bold tracking-tight">{t('history.title')}</h1>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder={t('common.search')} value={search} onChange={e => handleSearch(e.target.value)} className="pl-9" />
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {filterButtons.map(([key, label, count]) => (
            <Button key={key} variant={statusFilter === key ? "default" : "outline"} size="sm" className="rounded-full gap-1.5"
              onClick={() => { setFilter("statusFilter", key); fetchTasks(1) }}>
              {label}<span className="text-xs opacity-70">{count}</span>
            </Button>
          ))}
        </div>

        {selected.size > 0 && (
          <Card><CardContent className="flex flex-wrap items-center gap-3 p-3">
            <Button variant="ghost" size="sm" onClick={clearSelection}>
              <CheckSquare className="mr-1.5 h-4 w-4" />{t('common.deselect')}
            </Button>
            <span className="text-sm text-muted-foreground">{selected.size} {t('common.selected')}</span>
            <Button variant="destructive" size="sm" onClick={async () => {
              if (!confirm(t('history.confirmDeleteSelected', { count: selected.size }))) return
              try { await deleteSelected() } catch { alert(t('history.batchDeleteFailed')) }
            }}>
              <Trash2 className="mr-1.5 h-4 w-4" />{t('history.deleteSelected', { count: selected.size })}
            </Button>
            <div className="flex overflow-hidden rounded-lg border">
              <Button variant={downloadFormat === "md" ? "default" : "ghost"} size="sm" className="rounded-none" onClick={() => setDownloadFormat("md")}>MD</Button>
              <Button variant={downloadFormat === "pdf" ? "default" : "ghost"} size="sm" className="rounded-none" onClick={() => setDownloadFormat("pdf")}>PDF</Button>
            </div>
            <div className="flex-1" />
            <Button variant="outline" size="sm" onClick={handleBatchZip} disabled={downloading}>
              <Download className="mr-1.5 h-4 w-4" />{t('history.downloadZip')}
            </Button>
          </CardContent></Card>
        )}

        {filtered.length === 0 ? (
          <Card><CardContent className="flex flex-col items-center justify-center py-16">
            <p className="text-muted-foreground">{search ? t('history.noMatches') : t('history.noRecords')}</p>
          </CardContent></Card>
        ) : (
          <Card><div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                  <th className="w-8 px-3 py-2"><button onClick={selectAll} className="text-muted-foreground hover:text-foreground">{selected.size > 0 ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}</button></th>
                  <th className="px-3 py-2">{t('history.video')}</th>
                  <th className="w-28 px-3 py-2">{t('history.status')}</th>
                  <th className="px-3 py-2">{t('history.style')}</th>
                  <th className="px-3 py-2 text-right">{t('history.tokens')}</th>
                  <th className="whitespace-nowrap px-3 py-2">{t('history.created')}</th>
                  <th className="px-3 py-2 text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(item => {
                  const sc = statusConfig[item.status] || statusConfig.pending
                  const Icon = sc.icon
                  const canView = item.status === "completed"
                  const inFlight = item.status === "processing" || item.status === "pending" || item.status === "paused"
                  return (
                    <tr key={item.task_id} className={cn("border-b transition-colors hover:bg-muted/30", (canView || inFlight) && "cursor-pointer")}
                      onClick={() => { if (canView) navigate(`/note/${item.task_id}`); else if (inFlight) { setDetail(item); setLive(null) } }}>
                      <td className="px-3 py-2"><button onClick={e => { e.stopPropagation(); toggleSelect(item.task_id) }} className="text-muted-foreground hover:text-foreground">{selected.has(item.task_id) ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}</button></td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", sc.bg)}>
                            <Icon className={cn("h-4 w-4", sc.color, item.status === "processing" && "animate-spin")} />
                          </div>
                          <div className="min-w-0">
                            <p className="truncate font-medium">{item.videoName}</p>
                            {item.video_url && <p className="truncate text-xs text-muted-foreground"><ExternalLink className="mr-1 inline h-3 w-3" />{item.video_url}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="w-40 px-3 py-2">
                        <Badge variant={sc.variant} className="whitespace-nowrap">{t(`status.${item.status}`)}</Badge>
                        {inFlight && item.stage && (
                          <p className="mt-1 flex items-center gap-1 truncate text-[11px] text-muted-foreground">
                            <Activity className="h-3 w-3 shrink-0" />
                            <span className="truncate">{stageLabel(item.stage)}</span>
                            {item.status === "processing" && (
                              <span className="shrink-0 text-primary">{Math.round((item.progress || 0) * 100)}%</span>
                            )}
                          </p>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{t('noteStyle.' + (item.note_style || '')) || item.note_style || "-"}</td>
                      <td className="px-3 py-2 text-right font-mono text-xs">{item.totalTokens || "-"}</td>
                      <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{formatDate(item.createdAt)}</td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {canView && <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="h-8 w-8" onClick={e => { e.stopPropagation(); navigate(`/note/${item.task_id}`) }}><Eye className="h-4 w-4" /></Button></TooltipTrigger><TooltipContent>{t('history.viewNote')}</TooltipContent></Tooltip>}
                          {item.status === "failed" && <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="h-8 w-8" onClick={e => handleRetry(e, item.task_id)}><RotateCcw className="h-4 w-4" /></Button></TooltipTrigger><TooltipContent>{t('common.retry')}</TooltipContent></Tooltip>}
                          {inFlight && <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="h-8 w-8" onClick={e => { e.stopPropagation(); setDetail(item); setLive(null) }}><Activity className="h-4 w-4" /></Button></TooltipTrigger><TooltipContent>{t('history.openDetail')}</TooltipContent></Tooltip>}
                          {(item.status === "processing" || item.status === "paused") && <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="h-8 w-8" onClick={e => handlePauseResume(e, item)}>{item.status === "paused" ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}</Button></TooltipTrigger><TooltipContent>{item.status === "paused" ? t('history.resume') : t('history.pause')}</TooltipContent></Tooltip>}
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" className="h-8 w-8" onClick={e => e.stopPropagation()}><MoreVertical className="h-4 w-4" /></Button></DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              {canView && (<><DropdownMenuItem onClick={() => downloadNoteMd(item.task_id, (item.videoName || "note").replace(/\.[^.]+$/, "") + ".md")}><Download className="mr-2 h-4 w-4" />MD</DropdownMenuItem><DropdownMenuItem onClick={() => downloadNotePdf(item.task_id, (item.videoName || "note").replace(/\.[^.]+$/, "") + ".pdf")}><Download className="mr-2 h-4 w-4" />PDF</DropdownMenuItem></>)}
                              <DropdownMenuItem onClick={e => handleRename(e, item)}><Pencil className="mr-2 h-4 w-4" />{t('history.rename')}</DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={e => handleDelete(e, item.task_id)}><Trash2 className="mr-2 h-4 w-4" />{t('common.delete')}</DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div></Card>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => fetchTasks(page - 1)}>{"<"}</Button>
            <span className="px-3 text-sm text-muted-foreground">{page} / {totalPages}</span>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => fetchTasks(page + 1)}>{">"}</Button>
          </div>
        )}

        {/* 进行中任务的进展详情：点行或点「查看进展」打开，3 秒自动刷新 */}
        <Dialog open={!!detail} onOpenChange={(open) => { if (!open) { setDetail(null); setLive(null) } }}>
          <DialogContent className="max-w-lg">
            {detail && (() => {
              const v = { ...detail, ...(live || {}) }
              const pct = Math.round((v.progress || 0) * 100)
              const idx = STAGE_ORDER.indexOf(v.stage)
              const finished = v.status === "completed"
              const sc = statusConfig[v.status] || statusConfig.pending
              const Icon = sc.icon
              return (
                <>
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 pr-6 text-base">
                      <Icon className={cn("h-4 w-4 shrink-0", sc.color, v.status === "processing" && "animate-spin")} />
                      <span className="truncate">{v.videoName || v.filename}</span>
                    </DialogTitle>
                    <DialogDescription>{t('history.detailSubtitle')}</DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4">
                    <div className="rounded-lg border p-3">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{t('history.currentStage')}</span>
                        <span className="font-medium text-foreground">{stageLabel(v.stage)}</span>
                      </div>
                      <div className="mt-2 flex items-center gap-3">
                        <Progress value={finished ? 100 : pct} className="h-2" />
                        <span className="w-10 shrink-0 text-right font-mono text-xs text-muted-foreground">{finished ? 100 : pct}%</span>
                      </div>
                      <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                        <span>{t('history.elapsed')}: {elapsedText(v)}</span>
                        <Badge variant={sc.variant} className="whitespace-nowrap">{t(`status.${v.status}`)}</Badge>
                      </div>
                    </div>

                    {v.error && (
                      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
                        <p className="text-xs font-medium text-destructive">{t('status.failed')}</p>
                        <p className="mt-1 break-all text-[11px] leading-relaxed text-muted-foreground">{v.error}</p>
                      </div>
                    )}

                    <div className="space-y-1">
                      {STAGE_ORDER.map((s, i) => {
                        const state = finished || (idx >= 0 && i < idx) ? "done" : i === idx ? "current" : "pending"
                        return (
                          <div key={s} className={cn("flex items-center gap-2 rounded-md px-2 py-1 text-xs",
                            state === "current" && "bg-primary/5",
                            state === "pending" && "text-muted-foreground")}>
                            {state === "done" && <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />}
                            {state === "current" && <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />}
                            {state === "pending" && <span className="h-3.5 w-3.5 shrink-0 rounded-full border border-muted-foreground/30" />}
                            <span className="flex-1 truncate">{stageLabel(s)}</span>
                            <span className="shrink-0 text-[10px] text-muted-foreground">
                              {state === "done" ? t('history.stageDone') : state === "current" ? t('history.stageCurrent') : t('history.stagePending')}
                            </span>
                          </div>
                        )
                      })}
                    </div>

                    <div className="flex justify-end gap-2">
                      {(v.status === "processing" || v.status === "paused") && (
                        <Button size="sm" variant="outline" onClick={() => (v.status === "paused" ? resumeTask(v.task_id) : pauseTask(v.task_id))}>
                          {v.status === "paused" ? <><Play className="mr-1.5 h-3.5 w-3.5" />{t('history.resume')}</> : <><Pause className="mr-1.5 h-3.5 w-3.5" />{t('history.pause')}</>}
                        </Button>
                      )}
                      {v.status === "failed" && (
                        <Button size="sm" variant="outline" onClick={() => retryTask(v.task_id)}>
                          <RotateCcw className="mr-1.5 h-3.5 w-3.5" />{t('common.retry')}
                        </Button>
                      )}
                      {finished && (
                        <Button size="sm" onClick={() => navigate(`/note/${v.task_id}`)}>
                          <Eye className="mr-1.5 h-3.5 w-3.5" />{t('history.viewNote')}
                        </Button>
                      )}
                    </div>
                  </div>
                </>
              )
            })()}
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  )
}

export default HistoryPage
