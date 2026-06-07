import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileVideo, Loader2, X, Plus, Check, CheckCircle2, XCircle, Clock, FileText, ChevronDown, BookOpen, Zap, ListChecks, GraduationCap, Sparkles, RefreshCw, TrendingUp, AlertTriangle, BarChart3, Settings } from 'lucide-react'
import { uploadVideo, getHistoryAll, getTaskStatus, retryTask } from '../api/client'
import { useGlobalWebSocket } from '../hooks/useWebSocket'
import { useLang } from '../context/LangContext'

const STYLE_ICONS = { standard: BookOpen, summary: Zap, action: ListChecks, academic: GraduationCap, creative: Sparkles }
const STYLE_COLORS = { standard: '#4f8ef7', summary: '#f59e0b', action: '#10b981', academic: '#8b5cf6', creative: '#ec4899' }
const NOTE_STYLES = [
  { id: 'standard', zh: '标准笔记', en: 'Standard Notes', desc_zh: '结构化要点、细节和总结', desc_en: 'Structured key points, details and summary' },
  { id: 'summary', zh: '精简摘要', en: 'Brief Summary', desc_zh: '只保留核心要点，简洁明了', desc_en: 'Core points only, concise and clear' },
  { id: 'action', zh: '行动清单', en: 'Action Checklist', desc_zh: '提取可执行的步骤和方法', desc_en: 'Extract actionable steps and methods' },
  { id: 'academic', zh: '学术笔记', en: 'Academic Notes', desc_zh: '概念定义、理论框架和论证逻辑', desc_en: 'Concepts, frameworks and reasoning logic' },
  { id: 'creative', zh: '创意笔记', en: 'Creative Notes', desc_zh: '比喻、类比，生动易记', desc_en: 'Metaphors and analogies, vivid and memorable' },
]

function UploadPage() {
  const [files, setFiles] = useState([])
  const [lang, setLang] = useState('zh')
  const [noteStyle, setNoteStyle] = useState('standard')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [processingOptions, setProcessingOptions] = useState({
    max_concurrent_tasks: 2,
    keyframe_interval: 30,
    segment_duration: 300,
  })
  const [styleOpen, setStyleOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [over, setOver] = useState(false)
  const [history, setHistory] = useState([])
  const [uploadResults, setUploadResults] = useState([])
  const ref = useRef(null)
  const wsUpdates = useGlobalWebSocket()
  const nav = useNavigate()
  const { t, lang: globalLang } = useLang()

  useEffect(() => { getHistoryAll().then(setHistory).catch(err => console.warn('Failed to load history:', err)) }, [])

  // Sync WebSocket updates to upload results
  useEffect(() => {
    if (wsUpdates && wsUpdates.length > 0) {
      const latest = wsUpdates[wsUpdates.length - 1];
      setUploadResults(prev => prev.map(r => {
        if (r.task_id === latest.task_id) {
          return { ...r, status: latest.status, progress: latest.progress, stage: latest.stage };
        }
        return r;
      }));
    }
  }, [wsUpdates]);

  useEffect(() => {
    if (!uploadResults.length) return
    const pending = uploadResults.filter(r => r.task_id && r.status !== 'completed' && r.status !== 'failed')
    if (!pending.length) return
    const timer = setInterval(async () => {
      let changed = false
      const updated = await Promise.all(uploadResults.map(async r => {
        if (!r.task_id || r.status === 'completed' || r.status === 'failed') return r
        try {
          const s = await getTaskStatus(r.task_id)
          if (s.status !== r.status || s.progress !== r.progress) changed = true
          return { ...r, status: s.status, progress: s.progress, stage: s.stage }
        } catch { return r }
      }))
      if (changed) setUploadResults(updated)
    }, 2000)
    return () => clearInterval(timer)
  }, [uploadResults])

  const add = useCallback((fl) => {
    const vf = Array.from(fl).filter(f => /\.(mp4|avi|mov|mkv|wmv|flv|webm|m4v)$/i.test(f.name))
    setFiles(p => { const s = new Set(p.map(f => f.name+f.size)); return [...p, ...vf.filter(f => !s.has(f.name+f.size))] })
  }, [])

  const go = async () => {
    if (!files.length) return
    setUploading(true)
    setUploadResults([])
    const results = []
    for (const f of files) {
      try {
        const res = await uploadVideo(f, ()=>{}, lang, noteStyle, processingOptions)
        if (res.already_completed) {
          results.push({ ...res, fileName: f.name, fileSize: f.size, status: 'completed', progress: 1 })
        } else {
          results.push({ ...res, fileName: f.name, fileSize: f.size, status: 'pending', progress: 0 })
          if (res.duration_warning) {
            alert(res.duration_warning)
          }
        }
      } catch(e) {
        results.push({ fileName: f.name, fileSize: f.size, error: e.message, status: 'failed', progress: 0 })
      }
      setUploadResults([...results])
    }
    setUploading(false)
  }

  const handleRetry = async (e, taskId) => {
    e.stopPropagation()
    try { await retryTask(taskId); getHistory().then(setHistory).catch(() => {}) }
    catch (err) { alert(t.retryFailed) }
  }

  const completed = history.filter(h => h.status === 'completed').length
  const failed = history.filter(h => h.status === 'failed').length

  const statusMap = {
    completed: { icon: CheckCircle2, color: 'var(--green)', bg: 'var(--green-light)', label: t.completed, badge: 'badge-ok' },
    failed: { icon: XCircle, color: 'var(--red)', bg: 'var(--red-light)', label: t.failed, badge: 'badge-err' },
    processing: { icon: Loader2, color: 'var(--blue)', bg: 'var(--blue-light)', label: t.processing, badge: 'badge-proc' },
    pending: { icon: Clock, color: 'var(--gray-400)', bg: 'var(--gray-100)', label: t.pending, badge: 'badge-pending' },
  }

  const stageLabels = {
    zh: { queued: '排队中', extracting_audio: '提取音频', transcribing: '语音转文字', generating_outline: '生成大纲', extracting_keyframes: '提取关键帧', analyzing_content: '分析内容', generating_note: '生成笔记', completed: '完成' },
    en: { queued: 'Queued', extracting_audio: 'Extracting audio', transcribing: 'Transcribing', generating_outline: 'Generating outline', extracting_keyframes: 'Extracting keyframes', analyzing_content: 'Analyzing content', generating_note: 'Generating note', completed: 'Done' }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const mins = Math.floor((Date.now() - new Date(dateStr)) / 60000)
    if (mins < 1) return t.justNow
    if (mins < 60) return `${mins}${t.minsAgo}`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}${t.hoursAgo}`
    return `${Math.floor(hours / 24)}${t.daysAgo}`
  }

  const selectedStyle = NOTE_STYLES.find(s => s.id === noteStyle) || NOTE_STYLES[0]

  return (
    <div>
      {/* 顶部统计概览 */}
      <div className="stats">
        {[
          { val: history.length, label: t.totalVideos || '已处理视频', color: 'var(--blue)', icon: BarChart3, bg: 'var(--blue-light)' },
          { val: completed, label: t.totalNotes || '生成笔记', color: 'var(--green)', icon: TrendingUp, bg: 'var(--green-light)' },
          { val: failed, label: t.totalFailed || '处理失败', color: 'var(--red)', icon: AlertTriangle, bg: 'var(--red-light)' },
        ].map((s, i) => (
          <div key={i} className="stat-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="stat-val" style={{ color: s.color }}>{s.val}</div>
                <div className="stat-label">{s.label}</div>
              </div>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: s.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <s.icon size={20} color={s.color} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 主内容区 */}
      <div className="grid-2">
        {/* 左侧：上传卡片 */}
        <div className="card">
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Upload size={18} color="var(--blue)" /> {t.uploadTitle}
          </h2>

          {/* 语言 + 笔记风格 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 6 }}>{t.outputLang}</div>
              <div className="tags">
                <button className={`tag ${lang==='zh'?'on':''}`} onClick={()=>setLang('zh')}>
                  {lang==='zh' && <Check size={12} style={{marginRight:4}}/>}中文
                </button>
                <button className={`tag ${lang==='en'?'on':''}`} onClick={()=>setLang('en')}>
                  {lang==='en' && <Check size={12} style={{marginRight:4}}/>}English
                </button>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 6 }}>
                {globalLang === 'zh' ? '笔记风格' : 'Note Style'}
              </div>
              <div style={{ position: 'relative' }}>
                <button type="button" onClick={() => setStyleOpen(!styleOpen)}
                  style={{
                    width: '100%', padding: '7px 10px', borderRadius: 8,
                    border: '1.5px solid var(--gray-200)', background: 'white',
                    fontSize: 13, fontWeight: 500, color: 'var(--gray-700)',
                    cursor: 'pointer', outline: 'none', display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left',
                  }}>
                  {(() => { const Icon = STYLE_ICONS[noteStyle]; return <Icon size={14} color={STYLE_COLORS[noteStyle]} /> })()}
                  <span style={{ flex: 1 }}>{globalLang === 'zh' ? selectedStyle.zh : selectedStyle.en}</span>
                  <ChevronDown size={14} color="var(--gray-400)" style={{ transform: styleOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
                </button>
                {styleOpen && (
                  <div style={{
                    position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4,
                    background: 'white', border: '1.5px solid var(--gray-200)', borderRadius: 10,
                    boxShadow: '0 8px 24px rgba(0,0,0,0.1)', zIndex: 10, overflow: 'hidden',
                  }}>
                    {NOTE_STYLES.map(s => {
                      const Icon = STYLE_ICONS[s.id]
                      const active = noteStyle === s.id
                      return (
                        <button key={s.id} type="button" onClick={() => { setNoteStyle(s.id); setStyleOpen(false) }}
                          style={{
                            width: '100%', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 8,
                            background: active ? `${STYLE_COLORS[s.id]}08` : 'white',
                            border: 'none', cursor: 'pointer', textAlign: 'left', fontSize: 13,
                            borderBottom: '1px solid var(--gray-100)',
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = `${STYLE_COLORS[s.id]}10`}
                          onMouseLeave={e => e.currentTarget.style.background = active ? `${STYLE_COLORS[s.id]}08` : 'white'}>
                          <Icon size={14} color={STYLE_COLORS[s.id]} />
                          <span style={{ flex: 1, fontWeight: active ? 600 : 400, color: active ? STYLE_COLORS[s.id] : 'var(--gray-700)' }}>
                            {globalLang === 'zh' ? s.zh : s.en}
                          </span>
                          {active && <Check size={14} color={STYLE_COLORS[s.id]} />}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
              <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 4 }}>
                {globalLang === 'zh' ? selectedStyle.desc_zh : selectedStyle.desc_en}
              </div>
            </div>

            {/* Advanced Options */}
            <div>
              <button type="button" onClick={() => setShowAdvanced(!showAdvanced)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none',
                  cursor: 'pointer', fontSize: 11, fontWeight: 700, color: 'var(--gray-400)',
                  textTransform: 'uppercase', letterSpacing: 0.8, padding: 0,
                }}>
                <Settings size={12} />
                {t.advancedOptions}
                <ChevronDown size={12} style={{ transform: showAdvanced ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
              </button>
              {showAdvanced && (
                <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 10, padding: '10px 12px', background: 'var(--gray-50, #f9fafb)', borderRadius: 8, border: '1px solid var(--gray-200)' }}>
                  {/* Max Concurrent Tasks */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-700)' }}>{t.maxConcurrent}</span>
                      <span style={{ fontSize: 11, color: 'var(--gray-400)' }}>{processingOptions.max_concurrent_tasks} {t.tasks}</span>
                    </div>
                    <input type="range" min={1} max={5} step={1} value={processingOptions.max_concurrent_tasks}
                      onChange={e => setProcessingOptions(p => ({...p, max_concurrent_tasks: Number(e.target.value)}))}
                      style={{ width: '100%', accentColor: 'var(--blue)' }} />
                    <div style={{ fontSize: 10, color: 'var(--gray-400)' }}>{t.maxConcurrentDesc}</div>
                  </div>
                  {/* Keyframe Interval */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-700)' }}>{t.keyframeInterval}</span>
                      <span style={{ fontSize: 11, color: 'var(--gray-400)' }}>{processingOptions.keyframe_interval} {t.seconds}</span>
                    </div>
                    <input type="range" min={10} max={120} step={5} value={processingOptions.keyframe_interval}
                      onChange={e => setProcessingOptions(p => ({...p, keyframe_interval: Number(e.target.value)}))}
                      style={{ width: '100%', accentColor: 'var(--blue)' }} />
                    <div style={{ fontSize: 10, color: 'var(--gray-400)' }}>{t.keyframeIntervalDesc}</div>
                  </div>
                  {/* Segment Duration */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-700)' }}>{t.segmentDuration}</span>
                      <span style={{ fontSize: 11, color: 'var(--gray-400)' }}>{Math.floor(processingOptions.segment_duration / 60)}{globalLang === 'zh' ? '分钟' : 'min'} {processingOptions.segment_duration % 60}{t.seconds}</span>
                    </div>
                    <input type="range" min={60} max={1800} step={60} value={processingOptions.segment_duration}
                      onChange={e => setProcessingOptions(p => ({...p, segment_duration: Number(e.target.value)}))}
                      style={{ width: '100%', accentColor: 'var(--blue)' }} />
                    <div style={{ fontSize: 10, color: 'var(--gray-400)' }}>{t.segmentDurationDesc}</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 拖拽上传 */}
          <div className={`dropzone ${over?'over':''}`}
            onClick={()=>ref.current?.click()}
            onDragOver={e=>{e.preventDefault();setOver(true)}}
            onDragLeave={()=>setOver(false)}
            onDrop={e=>{e.preventDefault();setOver(false);add(e.dataTransfer.files)}}>
            <input ref={ref} type="file" accept="video/*" multiple onChange={e=>add(e.target.files)} style={{display:'none'}}/>
            <div className="dropzone-icon"><Plus size={20} color="var(--blue)"/></div>
            <div style={{fontWeight:600,fontSize:14,marginBottom:2}}>{t.dragHere}</div>
            <div style={{color:'var(--gray-400)',fontSize:12}}>{t.orClick} · {t.multiFiles}</div>
          </div>

          {/* 文件列表 */}
          {files.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>{t.selected} {files.length} {t.files}</span>
                <button className="btn btn-ghost btn-sm" onClick={() => { setFiles([]); setUploadResults([]) }} style={{ fontSize: 12 }}>{t.clear}</button>
              </div>
              {files.map((f, i) => {
                const r = uploadResults[i]
                return (
                  <div key={i} className="file-row in" style={{ marginBottom: 6 }}>
                    <div className="file-icon"><FileVideo size={14} color="var(--blue)"/></div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
                        <span style={{ color: 'var(--gray-400)', fontSize: 11, flexShrink: 0 }}>{(f.size/1048576).toFixed(1)} MB</span>
                        {r && r.task_id && (
                          <>
                            <span className={`badge ${statusMap[r.status]?.badge || 'badge-pending'}`} style={{ fontSize: 10, padding: '1px 6px' }}>
                              {statusMap[r.status]?.label || r.status}
                            </span>
                            {r.stage && r.status === 'processing' && (
                              <span style={{ fontSize: 11, color: 'var(--blue)' }}>
                                {(stageLabels[globalLang] || stageLabels.zh)[r.stage] || r.stage}
                              </span>
                            )}
                          </>
                        )}
                        {r && r.error && <span style={{ fontSize: 11, color: 'var(--red)' }}>{r.error}</span>}
                      </div>
                      {r && r.task_id && r.status === 'processing' && (
                        <div style={{ marginTop: 4, height: 3, background: 'var(--gray-100)', borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${(r.progress || 0) * 100}%`, background: 'var(--blue)', borderRadius: 2, transition: 'width 0.5s' }} />
                        </div>
                      )}
                      {r && r.task_id && r.status === 'completed' && (
                        <button className="btn btn-ghost btn-sm" style={{ fontSize: 11, padding: '2px 8px', marginTop: 4 }}
                          onClick={() => nav(`/note/${r.task_id}`)}>
                          {globalLang === 'zh' ? '查看笔记' : 'View Note'} →
                        </button>
                      )}
                    </div>
                    {!uploading && (
                      <button className="btn btn-ghost" style={{ padding: 4 }} onClick={e => { e.stopPropagation(); setFiles(p => p.filter((_, j) => j !== i)); setUploadResults(p => p.filter((_, j) => j !== i)) }}>
                        <X size={14} />
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          <button className="btn btn-primary btn-block" style={{ marginTop: 8 }} onClick={go} disabled={!files.length || uploading}>
            {uploading ? <><Loader2 size={16} className="spin" /> {t.uploading}</>
             : <><Upload size={16} /> {t.startProcess} {files.length > 0 && `(${files.length})`}</>}
          </button>
        </div>

        {/* 右侧：最近记录 */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexShrink: 0 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <FileText size={18} color="var(--blue)" /> {t.history}
            </h2>
            {history.length > 0 && (
              <button className="btn btn-ghost btn-sm" onClick={() => nav('/history')} style={{ fontSize: 12 }}>
                {t.viewAll || '查看全部'} →
              </button>
            )}
          </div>

          {history.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '36px 0', color: 'var(--gray-400)' }}>
              <FileText size={32} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
              <p style={{ fontSize: 13 }}>{t.noRecords}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', flex: 1, maxHeight: 420, paddingRight: 4 }}>
              {history.slice(0, 20).map((item) => {
                const s = statusMap[item.status] || statusMap.pending
                const Icon = s.icon
                return (
                  <div key={item.task_id} className="hist-row in"
                    onClick={() => item.status === 'completed' && nav(`/note/${item.task_id}`)}>
                    <div className="hist-icon" style={{ background: s.bg }}>
                      <Icon size={16} color={s.color} className={item.status === 'processing' ? 'spin' : ''} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.videoName}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 1 }}>{formatDate(item.createdAt)}</div>
                    </div>
                    <span className={`badge ${s.badge}`}>{s.label}</span>
                    {item.status === 'failed' && (
                      <button className="btn btn-ghost btn-sm" style={{ padding: 4, marginLeft: 4 }}
                        onClick={(e) => { e.stopPropagation(); handleRetry(e, item.task_id) }}>
                        <RefreshCw size={13} />
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default UploadPage

