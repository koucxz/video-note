import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload, FileVideo, Loader2, X, Plus, Check, CheckCircle2, XCircle,
  Clock, FileText, ChevronDown, BookOpen, Zap, ListChecks, GraduationCap,
  Sparkles, RefreshCw, TrendingUp, AlertTriangle, BarChart3, Settings,
} from 'lucide-react'
import { uploadVideo, getHistoryAll, getTaskStatus, retryTask } from '../api/client'
import { useGlobalWebSocket } from '../hooks/useWebSocket'
import { useNoteStyles } from '../hooks/useNoteStyles'
import { useLang } from '../context/LangContext'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Switch } from '../components/ui/switch'
import { Separator } from '../components/ui/separator'
import { Tooltip, TooltipProvider, TooltipTrigger, TooltipContent } from '../components/ui/tooltip'
import { cn } from '../lib/utils'

/* ─── 常量 ─── */
const STYLE_META = {
  standard:  { icon: BookOpen,    color: 'text-blue-600',   bg: 'bg-blue-50',   border: 'border-blue-200' },
  summary:   { icon: Zap,         color: 'text-amber-600',  bg: 'bg-amber-50',  border: 'border-amber-200' },
  action:    { icon: ListChecks,  color: 'text-emerald-600',bg: 'bg-emerald-50',border: 'border-emerald-200' },
  academic:  { icon: GraduationCap, color: 'text-violet-600',bg: 'bg-violet-50',border: 'border-violet-200' },
  detailed:  { icon: FileText,    color: 'text-cyan-600',   bg: 'bg-cyan-50',   border: 'border-cyan-200' },
  creative:  { icon: Sparkles,    color: 'text-pink-600',   bg: 'bg-pink-50',   border: 'border-pink-200' },
}

const STATUS_CFG = {
  completed:  { icon: CheckCircle2, variant: 'success',     color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  failed:     { icon: XCircle,      variant: 'destructive', color: 'text-destructive', bg: 'bg-destructive/10' },
  processing: { icon: Loader2,      variant: 'default',     color: 'text-primary',     bg: 'bg-primary/10' },
  pending:    { icon: Clock,        variant: 'secondary',   color: 'text-muted-foreground', bg: 'bg-muted' },
}

/* ─── 辅助 ─── */
function relativeTime(dateStr, t) {
  if (!dateStr) return ''
  const mins = Math.floor((Date.now() - new Date(dateStr)) / 60000)
  if (mins < 1) return t('time.justNow')
  if (mins < 60) return `${mins}${t('time.minsAgo')}`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}${t('time.hoursAgo')}`
  return `${Math.floor(hrs / 24)}${t('time.daysAgo')}`
}

/* 上传进度展示用的小工具 */
function fmtSize(n) {
  if (!n) return '0 MB'
  const mb = n / 1048576
  return mb >= 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(1)} MB`
}

function fmtSpeed(n) {
  if (!n) return '--'
  return n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB/s` : `${Math.max(0, Math.round(n / 1024))} KB/s`
}

function fmtEta(s) {
  if (s == null || !isFinite(s)) return '--:--'
  const total = Math.max(0, Math.round(s))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const sec = String(total % 60).padStart(2, '0')
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${sec}` : `${m}:${sec}`
}

function StatusBadge({ status, t }) {
  const cfg = STATUS_CFG[status] || STATUS_CFG.pending
  const statusKey = STATUS_CFG[status] ? status : 'pending'
  return <Badge variant={cfg.variant} className="text-xs">{t(`status.${statusKey}`)}</Badge>
}

/* ─── 页面 ─── */
export default function UploadPage() {
  const [files, setFiles] = useState([])
  const [lang, setLang] = useState('zh')
  const [noteStyle, setNoteStyle] = useState('standard')
  const [styleOpen, setStyleOpen] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [processingOptions, setProcessingOptions] = useState({ max_concurrent_tasks: 2, keyframe_interval: 30, segment_duration: 300, subtitle_only: false })
  const [uploading, setUploading] = useState(false)
  const [uploadPct, setUploadPct] = useState({})   // index -> { percent, loaded, total, speed, eta, phase }
  const [curIdx, setCurIdx] = useState(-1)
  const [over, setOver] = useState(false)
  const [history, setHistory] = useState([])
  const [results, setResults] = useState([])
  const ref = useRef(null)
  const styleRef = useRef(null)
  const wsUpdates = useGlobalWebSocket()
  const nav = useNavigate()
  const { t } = useLang()
  const { styles: noteStyles, loading: stylesLoading, error: stylesError } = useNoteStyles()

  useEffect(() => {
    if (noteStyles.length && !noteStyles.includes(noteStyle)) {
      setNoteStyle(noteStyles[0])
    }
  }, [noteStyles, noteStyle])

  /* 加载历史 */
  const loadHistory = () => { getHistoryAll().then(setHistory).catch(() => {}) }
  useEffect(() => { loadHistory() }, [])

  /* WebSocket 实时更新 */
  useEffect(() => {
    if (!wsUpdates?.length) return
    const latest = wsUpdates[wsUpdates.length - 1]
    setResults(prev => prev.map(r => r.task_id === latest.task_id ? { ...r, status: latest.status, progress: latest.progress, stage: latest.stage } : r))
  }, [wsUpdates])

  /* 结果变化时同步刷新历史 */
  useEffect(() => {
    if (results.some(r => r.status === 'completed' || r.status === 'failed')) loadHistory()
  }, [results])

  /* 轮询未完成任务 */
  useEffect(() => {
    const pending = results.filter(r => r.task_id && r.status !== 'completed' && r.status !== 'failed')
    if (!pending.length) return
    const timer = setInterval(async () => {
      let changed = false
      const updated = await Promise.all(results.map(async r => {
        if (!r.task_id || r.status === 'completed' || r.status === 'failed') return r
        try {
          const s = await getTaskStatus(r.task_id)
          if (s.status !== r.status || s.progress !== r.progress) changed = true
          return { ...r, status: s.status, progress: s.progress, stage: s.stage }
        } catch { return r }
      }))
      if (changed) setResults(updated)
    }, 2000)
    return () => clearInterval(timer)
  }, [results])

  /* 关闭下拉 */
  useEffect(() => {
    const handler = (e) => { if (styleRef.current && !styleRef.current.contains(e.target)) setStyleOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  /* 添加文件 */
  const add = useCallback((fl) => {
    const vf = Array.from(fl).filter(f => /\.(mp4|avi|mov|mkv|wmv|flv|webm|m4v)$/i.test(f.name))
    setFiles(p => { const s = new Set(p.map(f => f.name + f.size)); return [...p, ...vf.filter(f => !s.has(f.name + f.size))] })
  }, [])

  /* 上传处理 */
  const go = async () => {
    if (!files.length) return
    setUploading(true)
    setResults([])
    setUploadPct({})
    const out = []
    for (let i = 0; i < files.length; i++) {
      const f = files[i]
      setCurIdx(i)
      try {
        const res = await uploadVideo(
          f,
          (info) => setUploadPct((p) => ({ ...p, [i]: info })),
          lang, noteStyle, processingOptions,
        )
        if (res.already_completed) out.push({ ...res, fileName: f.name, fileSize: f.size, status: 'completed', progress: 1 })
        else out.push({ ...res, fileName: f.name, fileSize: f.size, status: 'pending', progress: 0 })
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.message || t('upload.uploadFailed')
        out.push({ fileName: f.name, fileSize: f.size, error: msg, status: 'failed', progress: 0 })
      }
      setResults([...out])
    }
    setUploading(false)
    setCurIdx(-1)
    setUploadPct({})
    // 刷新历史列表
    loadHistory()
  }

  const handleRetry = async (e, taskId) => {
    e.stopPropagation()
    try { await retryTask(taskId) } catch { alert(t('common.retryFailed')) }
  }

  /* 统计 */
  const completed = history.filter(h => h.status === 'completed').length
  const failed = history.filter(h => h.status === 'failed').length

  const selectedStyle = noteStyles.includes(noteStyle) ? noteStyle : noteStyles[0]
  const StyleIcon = STYLE_META[selectedStyle]?.icon || BookOpen

  /* ─── 渲染 ─── */
  return (
    <TooltipProvider>
      <div className="space-y-4">

        {/* ====== 统计概览 ====== */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            { val: history.length, label: t('upload.totalVideos'), icon: BarChart3, color: 'text-blue-600', bg: 'bg-blue-50' },
            { val: completed, label: t('upload.totalNotes'), icon: TrendingUp, color: 'text-emerald-600', bg: 'bg-emerald-50' },
            { val: failed, label: t('upload.totalFailed'), icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
          ].map((s, i) => (
            <Card key={i}>
              <CardContent className="flex items-center justify-between p-4">
                <div>
                  <p className={cn('text-2xl font-bold', s.color)}>{s.val}</p>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                </div>
                <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg', s.bg)}>
                  <s.icon className={cn('h-5 w-5', s.color)} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* ====== 主内容区 ====== */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">

          {/* ---- 左侧：上传 ---- */}
          <Card className="lg:col-span-3">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Upload className="h-4 w-4 text-primary" />
                {t('upload.title')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">

              {/* 语言选择 */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t('upload.outputLang')}</Label>
                <div className="flex gap-2">
                  {['zh', 'en'].map(l => (
                    <Button key={l} variant={lang === l ? 'default' : 'outline'} size="sm" className="rounded-full" onClick={() => setLang(l)}>
                      {lang === l && <Check className="mr-1 h-3 w-3" />}
                      {l === 'zh' ? t('language.chinese') : t('language.english')}
                    </Button>
                  ))}
                </div>
              </div>

              {/* 笔记风格 */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {t('upload.noteStyle')}
                </Label>
                <div className="relative" ref={styleRef}>
                  <button
                    type="button"
                    disabled={stylesLoading || !!stylesError || !selectedStyle}
                    onClick={() => setStyleOpen(!styleOpen)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50',
                      styleOpen && 'ring-2 ring-ring'
                    )}
                  >
                    <StyleIcon className={cn('h-4 w-4', STYLE_META[selectedStyle]?.color)} />
                    <span className="flex-1 text-left font-medium">{selectedStyle ? t('noteStyle.' + selectedStyle) : t('noteStyle.loading')}</span>
                    <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', styleOpen && 'rotate-180')} />
                  </button>
                  {styleOpen && (
                    <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-md border bg-popover shadow-md">
                      {noteStyles.map(id => {
                        const Icon = STYLE_META[id]?.icon || BookOpen
                        const active = noteStyle === id
                        return (
                          <button
                            key={id}
                            type="button"
                            onClick={() => { setNoteStyle(id); setStyleOpen(false) }}
                            className={cn(
                              'flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-accent',
                              active && 'bg-accent font-medium'
                            )}
                          >
                            <Icon className={cn('h-4 w-4', STYLE_META[id]?.color)} />
                            <span className="flex-1 text-left">{t('noteStyle.' + id)}</span>
                            {active && <Check className="h-4 w-4 text-primary" />}
                          </button>
                        )
                      })}
                    </div>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">
                    {stylesError ? t('noteStyle.unavailable') : selectedStyle ? t('noteStyle.' + selectedStyle + 'Desc') : t('noteStyle.loading')}
                  </p>
                </div>
              </div>

              {/* 高级选项 */}
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className={cn(
                    'flex w-full items-center justify-between rounded-md border-2 px-3 py-2 text-sm font-semibold transition-colors',
                    showAdvanced ? 'border-primary bg-primary/5 text-primary' : 'border-muted bg-muted/50 text-muted-foreground hover:border-muted-foreground/30'
                  )}
                >
                  <span className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    {t('upload.advancedOptions')}
                    {!showAdvanced && (
                      <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground">
                        {t('upload.concurrency')}: {processingOptions.max_concurrent_tasks} · {t('upload.kfShort')}: {processingOptions.keyframe_interval}s
                      </span>
                    )}
                  </span>
                  <ChevronDown className={cn('h-4 w-4 transition-transform', showAdvanced && 'rotate-180')} />
                </button>

                {showAdvanced && (
                  <Card className="border-muted">
                    <CardContent className="space-y-4 p-4">

                      {/* 并发数 */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs font-semibold">{t('upload.maxConcurrent')}</Label>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">{processingOptions.max_concurrent_tasks} {t('common.tasks')}</span>
                            <Input
                              type="number" min={1} max={5}
                              value={processingOptions.max_concurrent_tasks}
                              onChange={e => setProcessingOptions(p => ({ ...p, max_concurrent_tasks: Math.max(1, Math.min(5, Number(e.target.value) || 1)) }))}
                              className="h-7 w-16 text-center text-xs"
                            />
                          </div>
                        </div>
                        <input
                          type="range" min={1} max={5} step={1}
                          value={processingOptions.max_concurrent_tasks}
                          onChange={e => setProcessingOptions(p => ({ ...p, max_concurrent_tasks: Number(e.target.value) }))}
                          className="w-full accent-primary"
                        />
                        <p className="text-[11px] text-muted-foreground">{t('upload.maxConcurrentDesc')}</p>
                      </div>

                      <Separator />

                      {/* 关键帧间隔 */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs font-semibold">{t('upload.keyframeInterval')}</Label>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">{processingOptions.keyframe_interval}{t('common.seconds')}</span>
                            <Input
                              type="number" min={10} max={120}
                              value={processingOptions.keyframe_interval}
                              onChange={e => setProcessingOptions(p => ({ ...p, keyframe_interval: Math.max(10, Math.min(120, Number(e.target.value) || 30)) }))}
                              className="h-7 w-16 text-center text-xs"
                            />
                          </div>
                        </div>
                        <input
                          type="range" min={10} max={120} step={5}
                          value={processingOptions.keyframe_interval}
                          onChange={e => setProcessingOptions(p => ({ ...p, keyframe_interval: Number(e.target.value) }))}
                          className="w-full accent-primary"
                        />
                        <p className="text-[11px] text-muted-foreground">{t('upload.keyframeIntervalDesc')}</p>
                      </div>

                      <Separator />

                      {/* 分段时长 */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs font-semibold">{t('upload.segmentDuration')}</Label>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {Math.floor(processingOptions.segment_duration / 60)}{t('common.min')} {processingOptions.segment_duration % 60}{t('common.seconds')}
                            </span>
                            <Input
                              type="number" min={60} max={1800} step={60}
                              value={processingOptions.segment_duration}
                              onChange={e => setProcessingOptions(p => ({ ...p, segment_duration: Math.max(60, Math.min(1800, Number(e.target.value) || 300)) }))}
                              className="h-7 w-16 text-center text-xs"
                            />
                          </div>
                        </div>
                        <input
                          type="range" min={60} max={1800} step={60}
                          value={processingOptions.segment_duration}
                          onChange={e => setProcessingOptions(p => ({ ...p, segment_duration: Number(e.target.value) }))}
                          className="w-full accent-primary"
                        />
                        <p className="text-[11px] text-muted-foreground">
                          {t('upload.segmentDurationDesc')}
                        </p>
                      </div>

                      <Separator />

                      {/* 仅字幕模式 */}
                      <div className="flex items-center justify-between rounded-md border bg-background p-3">
                        <div>
                          <Label className="text-xs font-semibold">{t('upload.subtitleOnlyMode')}</Label>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            {t('upload.subtitleOnlyDesc')}
                          </p>
                        </div>
                        <Switch
                          checked={processingOptions.subtitle_only}
                          onCheckedChange={v => setProcessingOptions(p => ({ ...p, subtitle_only: v }))}
                        />
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

              <Separator />

              {/* 拖拽上传 */}
              <div
                className={cn(
                  'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors',
                  over ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'
                )}
                onClick={() => ref.current?.click()}
                onDragOver={e => { e.preventDefault(); setOver(true) }}
                onDragLeave={() => setOver(false)}
                onDrop={e => { e.preventDefault(); setOver(false); add(e.dataTransfer.files) }}
              >
                <input ref={ref} type="file" accept="video/*" multiple onChange={e => add(e.target.files)} className="hidden" />
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                  <Plus className="h-5 w-5 text-primary" />
                </div>
                <p className="text-sm font-semibold">{t('upload.dragHere')}</p>
                <p className="text-xs text-muted-foreground">{t('upload.orClick')} · {t('upload.multiFiles')}</p>
              </div>

              {/* 文件列表 */}
              {files.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{t('upload.selected')} {files.length} {t('upload.files')}</span>
                    <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => { setFiles([]); setResults([]) }}>{t('common.clear')}</Button>
                  </div>
                  <div className="max-h-48 space-y-1.5 overflow-y-auto">
                    {files.map((f, i) => {
                      const r = results[i]
                      return (
                        <div key={i} className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 transition-colors">
                          <FileVideo className="h-4 w-4 shrink-0 text-primary" />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">{f.name}</p>
                            <div className="mt-0.5 flex flex-wrap items-center gap-2">
                              <span className="text-[11px] text-muted-foreground">{fmtSize(f.size)}</span>
                              {r?.task_id && <StatusBadge status={r.status} t={t} />}
                              {r?.stage && r.status === 'processing' && (
                                <span className="text-[11px] text-primary">{t('processing.stage.' + r.stage)}</span>
                              )}
                              {r?.error && <span className="text-[11px] text-destructive">{r.error}</span>}
                            </div>
                            {/* 上传中：真实字节进度 + 速率 + 剩余时间 */}
                            {uploading && uploadPct[i] && (
                              <div className="mt-1.5 space-y-1">
                                <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                                  <div
                                    className={cn(
                                      'h-full rounded-full bg-primary transition-[width] duration-200 ease-out',
                                      uploadPct[i].phase === 'merging' && 'animate-pulse'
                                    )}
                                    style={{ width: `${Math.max(1.5, Math.min(100, uploadPct[i].percent))}%` }}
                                  />
                                </div>
                                <div className="flex items-center justify-between gap-2 text-[11px] tabular-nums text-muted-foreground">
                                  <span>
                                    {uploadPct[i].phase === 'merging'
                                      ? t('upload.merging')
                                      : `${uploadPct[i].percent.toFixed(1)}% · ${fmtSize(uploadPct[i].loaded)} / ${fmtSize(uploadPct[i].total)}`}
                                  </span>
                                  {uploadPct[i].phase !== 'merging' && (
                                    <span>
                                      {fmtSpeed(uploadPct[i].speed)} · {t('upload.remaining')} {fmtEta(uploadPct[i].eta)}
                                    </span>
                                  )}
                                </div>
                              </div>
                            )}
                            {r?.task_id && r.status === 'processing' && (
                              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                                <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${(r.progress || 0) * 100}%` }} />
                              </div>
                            )}
                            {r?.task_id && r.status === 'completed' && (
                              <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={() => nav(`/note/${r.task_id}`)}>
                                {t('upload.viewNote')} →
                              </Button>
                            )}
                          </div>
                          {!uploading && (
                            <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={() => { setFiles(p => p.filter((_, j) => j !== i)); setResults(p => p.filter((_, j) => j !== i)) }}>
                              <X className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* 提交按钮 */}
              <Button className="w-full" size="lg" onClick={go} disabled={!files.length || uploading || stylesLoading || !!stylesError || !selectedStyle}>
                {uploading
                  ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />{t('upload.uploading')}{uploadPct[curIdx] && uploadPct[curIdx].phase !== 'merging' ? ` ${Math.round(uploadPct[curIdx].percent)}%` : ''}</>
                  : <><Upload className="mr-2 h-4 w-4" />{t('upload.startProcess')}{files.length > 0 && ` (${files.length})`}</>
                }
              </Button>
            </CardContent>
          </Card>

          {/* ---- 右侧：历史 ---- */}
          <Card className="flex flex-col lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4 text-primary" />
                {t('header.history')}
              </CardTitle>
              {history.length > 0 && (
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => nav('/history')}>
                  {t('upload.viewAll')} →
                </Button>
              )}
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden pt-0">
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                  <FileText className="mb-2 h-8 w-8 opacity-40" />
                  <p className="text-sm">{t('upload.noRecords')}</p>
                </div>
              ) : (
                <div className="max-h-[28rem] space-y-1.5 overflow-y-auto pr-1">
                  {history.slice(0, 20).map(item => {
                    const cfg = STATUS_CFG[item.status] || STATUS_CFG.pending
                    const Icon = cfg.icon
                    const canView = item.status === 'completed'
                    return (
                      <div
                        key={item.task_id}
                        className={cn(
                          'flex items-center gap-2.5 rounded-md border px-3 py-2 transition-colors',
                          canView ? 'cursor-pointer hover:bg-accent' : 'hover:bg-muted/50'
                        )}
                        onClick={() => canView && nav(`/note/${item.task_id}`)}
                      >
                        <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-lg', cfg.bg)}>
                          <Icon className={cn('h-4 w-4', cfg.color, item.status === 'processing' && 'animate-spin')} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{item.videoName}</p>
                          <p className="text-[11px] text-muted-foreground">{relativeTime(item.createdAt, t)}</p>
                        </div>
                        <StatusBadge status={item.status} t={t} />
                        {item.status === 'failed' && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={e => handleRetry(e, item.task_id)}>
                                <RefreshCw className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>{t('common.retry')}</TooltipContent>
                          </Tooltip>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </TooltipProvider>
  )
}
