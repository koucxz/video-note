import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, RefreshCw, Loader2, Clock, CheckCircle2, XCircle, History, ArrowUpRight, ArrowLeft, Search, Download, CheckSquare, Square, FileText, Star, Copy, MoreVertical, ListFilter } from 'lucide-react'
import { getHistory, getHistoryAll, deleteTask, retryTask, downloadNoteMd, downloadNotePdf, downloadNotesZip } from '../api/client'
import { useLang } from '../context/LangContext'

function HistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const debounceTimer = useRef(null)
  const [selected, setSelected] = useState(new Set())
  const [downloading, setDownloading] = useState(false)
  const [downloadFormat, setDownloadFormat] = useState('md')
  const [statusFilter, setStatusFilter] = useState('all')
  const [favorites, setFavorites] = useState(() => { try { return new Set(JSON.parse(localStorage.getItem('vn_favorites') || '[]')) } catch { return new Set() } })
  const [contextMenu, setContextMenu] = useState(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const navigate = useNavigate()
  const { t, lang } = useLang()

  useEffect(() => { loadHistory() }, [])

  // Debounce search input
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => setDebouncedSearch(search), 300)
    return () => { if (debounceTimer.current) clearTimeout(debounceTimer.current) }
  }, [search])

  const loadHistory = async (p = 1) => {
    try {
      setLoading(true)
      const resp = await getHistory(p, 20)
      setHistory(resp.items || [])
      setTotalPages(resp.pages || 1)
      setTotal(resp.total || 0)
      setPage(p)
    }
    catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  const handleDelete = async (e, taskId) => {
    e.stopPropagation()
    if (!confirm(t.confirmDelete)) return
    try { await deleteTask(taskId); setHistory(history.filter(i => i.task_id !== taskId)); setSelected(s => { const n = new Set(s); n.delete(taskId); return n }) }
    catch (err) { alert(t.deleteFailed) }
  }

  const handleRetry = async (e, taskId) => {
    e.stopPropagation()
    try { await retryTask(taskId); loadHistory() }
    catch (err) { alert(t.retryFailed) }
  }

  const toggleFavorite = (e, taskId) => {
    e.stopPropagation()
    setFavorites(prev => {
      const n = new Set(prev)
      n.has(taskId) ? n.delete(taskId) : n.add(taskId)
      localStorage.setItem('vn_favorites', JSON.stringify([...n]))
      return n
    })
  }

  const handleContextMenu = (e, item) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, item })
  }

  const closeContextMenu = () => setContextMenu(null)

  useEffect(() => {
    if (contextMenu) {
      const handler = () => closeContextMenu()
      document.addEventListener('click', handler)
      return () => document.removeEventListener('click', handler)
    }
  }, [contextMenu])

  const toggleSelect = (taskId) => {
    setSelected(s => { const n = new Set(s); n.has(taskId) ? n.delete(taskId) : n.add(taskId); return n })
  }

  const toggleSelectAll = () => {
    const completedIds = filtered.filter(i => i.status === 'completed').map(i => i.task_id)
    if (completedIds.every(id => selected.has(id))) {
      setSelected(new Set())
    } else {
      setSelected(new Set(completedIds))
    }
  }

  const doDownload = (taskId, name) => {
    const base = (name || 'note').replace(/\.[^.]+$/, '')
    if (downloadFormat === 'pdf') {
      downloadNotePdf(taskId, base + '.pdf')
    } else {
      downloadNoteMd(taskId, base + '.md')
    }
  }

  const handleBatchDownloadZip = async () => {
    if (!selected.size) return
    if (!confirm(t.confirmDownload || 'Download as ZIP?')) return
    setDownloading(true)
    try { await downloadNotesZip([...selected], downloadFormat) }
    catch (err) { alert('Download failed') }
    finally { setDownloading(false) }
  }

  const handleBatchDownload = async () => {
    if (!selected.size) return
    if (!confirm(t.confirmDownload || `Download ${selected.size} notes as ZIP?`)) return
    setDownloading(true)
    try { await downloadNotesZip([...selected]) }
    catch (err) { alert('下载失败') }
    finally { setDownloading(false) }
  }

  const handleBatchDownloadMd = async () => {
    if (!selected.size) return
    if (!confirm(t.confirmDownloadMd || `Download ${selected.size} notes as MD files?`)) return
    setDownloading(true)
    try {
      const ids = [...selected]
      for (const id of ids) {
        const item = history.find(h => h.task_id === id)
        if (item) {
          const name = (item.videoName || 'note').replace(/\.[^.]+$/, '') + '.md'
          await downloadNoteMd(id, name)
          await new Promise(r => setTimeout(r, 300))
        }
      }
    } catch (err) { alert('下载失败') }
    finally { setDownloading(false) }
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

  const formatTokens = (n) => {
    if (!n || n === 0) return null
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
    return String(n)
  }

  const statusMap = {
    completed: { icon: CheckCircle2, color: 'var(--green)', bg: 'var(--green-light)', label: t.completed, badge: 'badge-ok' },
    failed: { icon: XCircle, color: 'var(--red)', bg: 'var(--red-light)', label: t.failed, badge: 'badge-err' },
    processing: { icon: Loader2, color: 'var(--blue)', bg: 'var(--blue-light)', label: t.processing, badge: 'badge-proc' },
    pending: { icon: Clock, color: 'var(--gray-400)', bg: 'var(--gray-100)', label: t.pending, badge: 'badge-pending' },
  }

  const filtered = history.filter(h => {
    if (debouncedSearch && !h.videoName?.toLowerCase().includes(debouncedSearch.toLowerCase())) return false
    if (statusFilter !== 'all' && h.status !== statusFilter) return false
    return true
  })
  const completedCount = filtered.filter(i => i.status === 'completed').length

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <Loader2 size={36} className="spin" color="var(--blue)" />
    </div>
  )

  return (
    <div>
      {/* 工具栏 */}
      <div className="history-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')} style={{ padding: '4px 8px' }}>
            <ArrowLeft size={16} />
          </button>
          <h1 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.5px' }}>{t.history}</h1>
          <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>{t.totalRecords} {total} {t.records}</span>
        </div>
        <div className="search-box" style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '7px 12px', borderRadius: 'var(--radius-sm)',
          background: 'var(--white)', border: '1px solid var(--gray-200)', width: 240,
        }}>
          <Search size={14} color="var(--gray-400)" />
          <input type="text" placeholder="搜索记录..." value={search} onChange={e => setSearch(e.target.value)}
            style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: 13, flex: 1, color: 'var(--gray-900)', fontFamily: 'inherit' }} />
        </div>
      </div>

      {/* 状态筛选 */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        {[['all', lang === 'zh' ? '全部' : 'All'], ['completed', t.completed], ['processing', t.processing], ['failed', t.failed], ['pending', t.pending]].map(([key, label]) => (
          <button key={key} onClick={() => setStatusFilter(key)} style={{
            padding: '5px 14px', borderRadius: 100, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500, fontFamily: 'inherit',
            background: statusFilter === key ? 'var(--blue)' : 'var(--gray-100)',
            color: statusFilter === key ? 'white' : 'var(--gray-500)',
          }}>{label}</button>
        ))}
      </div>

      {/* 批量操作栏 */}
      {completedCount > 0 && (
<div className="batch-bar" style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, padding: '10px 14px', background: 'var(--white)', borderRadius: 10, border: '1px solid var(--gray-200)', flexWrap: 'wrap' }}>
          <button className="btn btn-ghost btn-sm" onClick={toggleSelectAll} style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
            {completedCount > 0 && completedCount === selected.size ? <CheckSquare size={14} /> : <Square size={14} />}
            {selected.size > 0 ? `已选 ${selected.size} 项` : '全选'}
          </button>
          <div style={{ display: 'flex', alignItems: 'center', border: '1px solid var(--gray-200)', borderRadius: 8, overflow: 'hidden' }}>
            <button onClick={() => setDownloadFormat('md')} style={{
              padding: '5px 14px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500, fontFamily: 'inherit',
              background: downloadFormat === 'md' ? 'var(--blue)' : 'var(--white)',
              color: downloadFormat === 'md' ? 'white' : 'var(--gray-500)',
            }}>{lang === 'zh' ? '下载MD' : 'MD'}</button>
            <button onClick={() => setDownloadFormat('pdf')} style={{
              padding: '5px 14px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500, fontFamily: 'inherit',
              background: downloadFormat === 'pdf' ? 'var(--blue)' : 'var(--white)',
              color: downloadFormat === 'pdf' ? 'white' : 'var(--gray-500)',
            }}>{lang === 'zh' ? '下载PDF' : 'PDF'}</button>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn btn-outline btn-sm" onClick={handleBatchDownloadZip} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
            {t.downloadZip} {selected.size > 0 && `(${selected.size})`}
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleBatchDownload} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
            {downloadFormat === 'pdf' ? (lang === 'zh' ? '下载PDF' : 'PDF') : (lang === 'zh' ? '下载MD' : 'MD')} {selected.size > 0 && `(${selected.size})`}
          </button>
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '56px 24px' }}>
          <div className="dropzone-icon" style={{ margin: '0 auto 14px' }}>
            <History size={28} color="var(--blue)" />
          </div>
          <p style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>{search ? '未找到匹配记录' : t.noRecords}</p>
          {!search && <p style={{ color: 'var(--gray-400)', fontSize: 13, marginBottom: 20 }}>{t.uploadFirst}</p>}
          <button className="btn btn-primary" onClick={() => navigate('/')}>{t.upload}</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 10 }}>
          {filtered.map((item) => {
            const s = statusMap[item.status] || statusMap.pending
            const Icon = s.icon
            const canView = item.status === 'completed'
            const isSelected = selected.has(item.task_id)
            return (
              <div key={item.task_id} className="hist-row in"
                onClick={() => canView && navigate(`/note/${item.task_id}`)}
                style={{ padding: '12px 14px', background: isSelected ? 'var(--blue-light)' : undefined }}>
                <div className="checkbox-col" style={{ display: 'flex', alignItems: 'center' }}>
                  {canView && (
                    <button onClick={(e) => { e.stopPropagation(); toggleSelect(item.task_id) }}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, display: 'flex' }}>
                      {isSelected ? <CheckSquare size={16} color="var(--blue)" /> : <Square size={16} color="var(--gray-300)" />}
                    </button>
                  )}
                </div>
                <div className="hist-icon" style={{ background: s.bg, width: 36, height: 36, borderRadius: 8 }}>
                  <Icon size={16} color={s.color} className={item.status === 'processing' ? 'spin' : ''} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.videoName}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 1 }}>
                    <span style={{ fontSize: 11, color: 'var(--gray-400)' }}>{formatDate(item.createdAt)}</span>
                    {formatTokens(item.totalTokens) && (
                      <span style={{ fontSize: 10, color: 'var(--gray-400)', background: 'var(--gray-100)', padding: '1px 5px', borderRadius: 4 }}>
                        {formatTokens(item.totalTokens)} tokens
                      </span>
                    )}
                  </div>
                </div>
                <span className={`badge ${s.badge}`}>{s.label}</span>
                <div style={{ display: 'flex', gap: 2, alignItems: 'center', marginLeft: 4 }}>
                  {canView && (
                    <button className="btn btn-primary btn-sm" style={{ padding: '4px 10px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); navigate(`/note/${item.task_id}`) }}>
                      <ArrowUpRight size={12} /> {t.view}
                    </button>
                  )}
                  {canView && (
                    <button className="btn btn-ghost btn-sm" style={{ padding: '4px 8px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); doDownload(item.task_id, item.videoName) }}
                      title={downloadFormat === 'pdf' ? (lang === 'zh' ? '下载PDF' : 'PDF') : (lang === 'zh' ? '下载MD' : 'MD')}>
                      <Download size={12} />
                    </button>
                  )}
                  {item.status === 'failed' && (
                    <button className="btn btn-ghost btn-sm" style={{ padding: 4 }} onClick={(e) => handleRetry(e, item.task_id)}>
                      <RefreshCw size={13} />
                    </button>
                  )}
                  <button className="btn btn-ghost btn-sm" style={{ color: 'var(--gray-400)', padding: 4 }}
                    onClick={(e) => handleDelete(e, item.task_id)}>
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
          <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => loadHistory(page - 1)}>
            {'<'}
          </button>
          <span style={{ fontSize: 13, color: 'var(--gray-500)', padding: '6px 12px' }}>
            {page} / {totalPages}
          </span>
          <button className="btn btn-outline btn-sm" disabled={page >= totalPages} onClick={() => loadHistory(page + 1)}>
            {'>'}
          </button>
        </div>
      )}
      {/* Context Menu */}
      {contextMenu && (
        <div style={{
          position: 'fixed', top: contextMenu.y, left: contextMenu.x, zIndex: 9999,
          background: 'white', borderRadius: 10, border: '1px solid var(--gray-200)',
          boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4, minWidth: 160,
        }}>
          {contextMenu.item.status === 'completed' && (
            <button onClick={() => { navigate(`/note/${contextMenu.item.task_id}`); closeContextMenu() }}
              style={ctxBtnStyle}>
              <ArrowUpRight size={14} /> {lang === 'zh' ? '查看笔记' : 'View Note'}
            </button>
          )}
          {contextMenu.item.status === 'completed' && (
            <button onClick={() => { doDownload(contextMenu.item.task_id, contextMenu.item.videoName); closeContextMenu() }}
              style={ctxBtnStyle}>
              <Download size={14} /> {downloadFormat === 'pdf' ? (lang === 'zh' ? '下载PDF' : 'PDF') : (lang === 'zh' ? '下载MD' : 'MD')}
            </button>
          )}
          <button onClick={() => { toggleFavorite({stopPropagation:()=>{}}, contextMenu.item.task_id); closeContextMenu() }}
            style={ctxBtnStyle}>
            <Star size={14} /> {favorites.has(contextMenu.item.task_id) ? (lang === 'zh' ? '取消收藏' : 'Unstar') : (lang === 'zh' ? '收藏' : 'Star')}
          </button>
          {contextMenu.item.status === 'completed' && (
            <button onClick={() => { navigator.clipboard.writeText(contextMenu.item.task_id); closeContextMenu() }}
              style={ctxBtnStyle}>
              <Copy size={14} /> {lang === 'zh' ? '复制ID' : 'Copy ID'}
            </button>
          )}
          {contextMenu.item.status === 'failed' && (
            <button onClick={() => { handleRetry({stopPropagation:()=>{}}, contextMenu.item.task_id); closeContextMenu() }}
              style={ctxBtnStyle}>
              <RefreshCw size={14} /> {t.retry}
            </button>
          )}
          <div style={{ height: 1, background: 'var(--gray-100)', margin: '4px 0' }} />
          <button onClick={() => { handleDelete({stopPropagation:()=>{}}, contextMenu.item.task_id); closeContextMenu() }}
            style={{...ctxBtnStyle, color: 'var(--red)'}}>
            <Trash2 size={14} /> {t.delete}
          </button>
        </div>
      )}
    </div>
  )
}

const ctxBtnStyle = {
  display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '7px 12px',
  border: 'none', background: 'none', cursor: 'pointer', fontSize: 13, fontFamily: 'inherit',
  color: 'var(--gray-700)', borderRadius: 6,
}

export default HistoryPage
