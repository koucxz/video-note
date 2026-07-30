import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload, FileVideo, Loader2, X, Plus, Check, CheckCircle2, XCircle,
  Clock, FileText, ChevronDown, BookOpen, Zap, ListChecks, GraduationCap,
  Sparkles, RefreshCw, TrendingUp, AlertTriangle, BarChart3, Settings,
} from 'lucide-react'
import { uploadVideo, getHistoryAll, getTaskStatus, retryTask } from '../api/client'
import { useGlobalWebSocket } from '../hooks/useWebSocket'
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
  creative:  { icon: Sparkles,    color: 'text-pink-600',   bg: 'bg-pink-50',   border: 'border-pink-200' },
}

const NOTE_STYLES = [
  { id: 'standard', zh: '标准笔记', en: 'Standard Notes', desc_zh: '结构化要点、细节和总结', desc_en: 'Structured key points, details and summary' },
  { id: 'summary',  zh: '精简摘要', en: 'Brief Summary',   desc_zh: '只保留核心要点，简洁明了', desc_en: 'Core points only, concise and clear' },
  { id: 'action',   zh: '行动清单', en: 'Action Checklist',desc_zh: '提取可执行的步骤和方法',   desc_en: 'Extract actionable steps and methods' },
  { id: 'academic', zh: '学术笔记', en: 'Academic Notes',  desc_zh: '概念定义、理论框架和论证逻辑', desc_en: 'Concepts, frameworks and reasoning logic' },
  { id: 'creative', zh: '创意笔记', en: 'Creative Notes',  desc_zh: '比喻、类比，生动易记',       desc_en: 'Metaphors and analogies, vivid and memorable' },
]

const STATUS_CFG = {
  completed:  { icon: CheckCircle2, variant: 'success',     color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  failed:     { icon: XCircle,      variant: 'destructive', color: 'text-destructive', bg: 'bg-destructive/10' },
  processing: { icon: Loader2,      variant: 'default',     color: 'text-primary',     bg: 'bg-primary/10' },
  pending:    { icon: Clock,        variant: 'secondary',   color: 'text-muted-foreground', bg: 'bg-muted' },
}

const STAGE_LABELS = {
  zh: { queued: '排队中', extracting_audio: '提取音频', transcribing: '语音转文字', generating_outline: '生成大纲', extracting_keyframes: '提取关键帧', analyzing_content: '分析内容', generating_note: '生成笔记', completed: '完成' },
  en: { queued: 'Queued', extracting_audio: 'Audio', transcribing: 'Transcribe', generating_outline: 'Outline', extracting_keyframes: 'Frames', analyzing_content: 'Analyze', generating_note: 'Note', completed: 'Done' },
}

/* ─── 辅助 ─── */
function relativeTime(dateStr, t) {
  if (!dateStr) return ''
  const mins = Math.floor((Date.now() - new Date(dateStr)) / 60000)
  if (mins < 1) return t.justNow
  if (mins < 60) return `${mins}${t.minsAgo}`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}${t.hoursAgo}`
  return `${Math.floor(hrs / 24)}${t.daysAgo}`
}

function StatusBadge({ status, lang }) {
  const cfg = STATUS_CFG[status] || STATUS_CFG.pending
  const labels = { completed: lang === 'zh' ? '已完成' : 'Done', failed: lang === 'zh' ? '失败' : 'Failed', processing: lang === 'zh' ? '处理中' : 'Running', pending: lang === 'zh' ? '等待中' : 'Pending' }
  return <Badge variant={cfg.variant} className="text-xs">{labels[status] || status}</Badge>
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
  const [over, setOver] = useState(false)
  const [history, setHistory] = useState([])
  const [results, setResults] = useState([])
  const ref = useRef(null)
  const styleRef = useRef(null)
  const wsUpdates = useGlobalWebSocket()
  const nav = useNavigate()
  const { t, lang: gLang } = useLang()

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
    const out = []
    for (const f of files) {
      try {
        const res = await uploadVideo(f, () => {}, lang, noteStyle, processingOptions)
        if (res.already_completed) out.push({ ...res, fileName: f.name, fileSize: f.size, status: 'completed', progress: 1 })
        else out.push({ ...res, fileName: f.name, fileSize: f.size, status: 'pending', progress: 0 })
      } catch (e) { out.push({ fileName: f.name, fileSize: f.size, error: e.message, status: 'failed', progress: 0 }) }
      setResults([...out])
    }
    setUploading(false)
    // 刷新历史列表
    loadHistory()
  }

  const handleRetry = async (e, taskId) => {
    e.stopPropagation()
    try { await retryTask(taskId) } catch { alert(t.retryFailed) }
  }

  /* 统计 */
  const completed = history.filter(h => h.status === 'completed').length
  const failed = history.filter(h => h.status === 'failed').length

  const selectedStyle = NOTE_STYLES.find(s => s.id === noteStyle) || NOTE_STYLES[0]
  const StyleIcon = STYLE_META[noteStyle]?.icon || BookOpen

  /* ─── 渲染 ─── */
  return (
    <TooltipProvider>
      <div className="space-y-4">

        {/* ====== 统计概览 ====== */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { val: history.length, label: t.totalVideos, icon: BarChart3, color: 'text-blue-600', bg: 'bg-blue-50' },
            { val: completed, label: t.totalNotes, icon: TrendingUp, color: 'text-emerald-600', bg: 'bg-emerald-50' },
            { val: failed, label: t.totalFailed, icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
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
                {t.uploadTitle}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">

              {/* 语言选择 */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t.outputLang}</Label>
                <div className="flex gap-2">
                  {['zh', 'en'].map(l => (
                    <Button key={l} variant={lang === l ? 'default' : 'outline'} size="sm" className="rounded-full" onClick={() => setLang(l)}>
                      {lang === l && <Check className="mr-1 h-3 w-3" />}
                      {l === 'zh' ? '中文' : 'English'}
                    </Button>
                  ))}
                </div>
              </div>

              {/* 笔记风格 */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {gLang === 'zh' ? '笔记风格' : 'Note Style'}
                </Label>
                <div className="relative" ref={styleRef}>
                  <button
                    type="button"
                    onClick={() => setStyleOpen(!styleOpen)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm transition-colors hover:bg-accent',
                      styleOpen && 'ring-2 ring-ring'
                    )}
                  >
                    <StyleIcon className={cn('h-4 w-4', STYLE_META[noteStyle]?.color)} />
                    <span className="flex-1 text-left font-medium">{gLang === 'zh' ? selectedStyle.zh : selectedStyle.en}</span>
                    <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', styleOpen && 'rotate-180')} />
                  </button>
                  {styleOpen && (
                    <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-md border bg-popover shadow-md">
                      {NOTE_STYLES.map(s => {
                        const Icon = STYLE_META[s.id]?.icon || BookOpen
                        const active = noteStyle === s.id
                        return (
                          <button
                            key={s.id}
                            type="button"
                            onClick={() => { setNoteStyle(s.id); setStyleOpen(false) }}
                            className={cn(
                              'flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-accent',
                              active && 'bg-accent font-medium'
                            )}
                          >
                            <Icon className={cn('h-4 w-4', STYLE_META[s.id]?.color)} />
                            <span className="flex-1 text-left">{gLang === 'zh' ? s.zh : s.en}</span>
                            {active && <Check className="h-4 w-4 text-primary" />}
                          </button>
                        )
                      })}
                    </div>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">{gLang === 'zh' ? selectedStyle.desc_zh : selectedStyle.desc_en}</p>
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
                    {t.advancedOptions}
                    {!showAdvanced && (
                      <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground">
                        {gLang === 'zh' ? '并发' : 'Conc'}: {processingOptions.max_concurrent_tasks} · {gLang === 'zh' ? '帧间隔' : 'KF'}: {processingOptions.keyframe_interval}s
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
                          <Label className="text-xs font-semibold">{t.maxConcurrent}</Label>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">{processingOptions.max_concurrent_tasks} {t.tasks}</span>
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
                        <p className="text-[11px] text-muted-foreground">{t.maxConcurrentDesc}</p>
                      </div>

                      <Separator />

                      {/* 关键帧间隔 */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs font-semibold">{t.keyframeInterval}</Label>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">{processingOptions.keyframe_interval}{t.seconds}</span>
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
                        <p className="text-[11px] text-muted-foreground">{t.keyframeIntervalDesc}</p>
                      </div>

                      <Separator />

                      {/* 分段时长 */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs font-semibold">{t.segmentDuration}</Label>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {Math.floor(processingOptions.segment_duration / 60)}{gLang === 'zh' ? '分钟' : 'min'} {processingOptions.segment_duration % 60}{t.seconds}
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
                          {gLang === 'zh' ? '超过此时长的视频会自动分段处理' : 'Videos longer than this are auto-split into segments'}
                        </p>
                      </div>

                      <Separator />

                      {/* 仅字幕模式 */}
                      <div className="flex items-center justify-between rounded-md border bg-background p-3">
                        <div>
                          <Label className="text-xs font-semibold">{gLang === 'zh' ? '仅字幕模式' : 'Subtitle Only Mode'}</Label>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            {gLang === 'zh' ? '跳过AI分析，仅提取视频字幕文字并生成笔记' : 'Skip AI analysis, extract subtitle text and generate notes'}
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
                <p className="text-sm font-semibold">{t.dragHere}</p>
                <p className="text-xs text-muted-foreground">{t.orClick} · {t.multiFiles}</p>
              </div>

              {/* 文件列表 */}
              {files.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{t.selected} {files.length} {t.files}</span>
                    <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => { setFiles([]); setResults([]) }}>{t.clear}</Button>
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
                              <span className="text-[11px] text-muted-foreground">{(f.size / 1048576).toFixed(1)} MB</span>
                              {r?.task_id && <StatusBadge status={r.status} lang={gLang} />}
                              {r?.stage && r.status === 'processing' && (
                                <span className="text-[11px] text-primary">{(STAGE_LABELS[gLang] || STAGE_LABELS.zh)[r.stage]}</span>
                              )}
                              {r?.error && <span className="text-[11px] text-destructive">{r.error}</span>}
                            </div>
                            {r?.task_id && r.status === 'processing' && (
                              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                                <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${(r.progress || 0) * 100}%` }} />
                              </div>
                            )}
                            {r?.task_id && r.status === 'completed' && (
                              <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={() => nav(`/note/${r.task_id}`)}>
                                {gLang === 'zh' ? '查看笔记' : 'View Note'} →
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
              <Button className="w-full" size="lg" onClick={go} disabled={!files.length || uploading}>
                {uploading
                  ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />{t.uploading}</>
                  : <><Upload className="mr-2 h-4 w-4" />{t.startProcess}{files.length > 0 && ` (${files.length})`}</>
                }
              </Button>
            </CardContent>
          </Card>

          {/* ---- 右侧：历史 ---- */}
          <Card className="flex flex-col lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4 text-primary" />
                {t.history}
              </CardTitle>
              {history.length > 0 && (
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => nav('/history')}>
                  {t.viewAll} →
                </Button>
              )}
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden pt-0">
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                  <FileText className="mb-2 h-8 w-8 opacity-40" />
                  <p className="text-sm">{t.noRecords}</p>
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
                        <StatusBadge status={item.status} lang={gLang} />
                        {item.status === 'failed' && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={e => handleRetry(e, item.task_id)}>
                                <RefreshCw className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>{t.retry}</TooltipContent>
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
