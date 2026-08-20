import pathlib

hp = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = hp.read_text(encoding="utf-8")

# 1. Add downloadFormat state after downloading state
old = "  const [downloading, setDownloading] = useState(false)"
new = "  const [downloading, setDownloading] = useState(false)\n  const [downloadFormat, setDownloadFormat] = useState('md')"
t = t.replace(old, new, 1)

# 2. Add download helper that uses the format
old_download = "  const handleBatchDownload = async () => {"
new_download = """  const doDownload = (taskId, name) => {
    const base = (name || 'note').replace(/\\.[^.]+$/, '')
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

  const handleBatchDownload = async () => {"""
t = t.replace(old_download, new_download, 1)

# 3. Remove old handleBatchDownloadMd and replace handleBatchDownload body
old_batch_body = """    if (!selected.size) return
    if (!confirm(t.confirmDownload || `Download ${selected.size} notes as ZIP?`)) return
    setDownloading(true)
    try { await downloadNotesZip([...selected]) }
    catch (err) { alert('\u6d41\u4e0b\u8f7d\u5931\u8d25') }
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
          const name = (item.videoName || 'note').replace(/\\.[^.]+$/, '') + '.md'
          await downloadNoteMd(id, name)
          await new Promise(r => setTimeout(r, 300))
        }
      }
    } catch (err) { alert('\u6d41\u4e0b\u8f7d\u5931\u8d25') }
    finally { setDownloading(false) }
  }"""
new_batch_body = """    if (!selected.size) return
    const fmt = downloadFormat.toUpperCase()
    if (!confirm(`Download ${selected.size} notes as ${fmt}?`)) return
    setDownloading(true)
    try {
      const ids = [...selected]
      for (const id of ids) {
        const item = history.find(h => h.task_id === id)
        if (item) {
          doDownload(id, item.videoName)
          await new Promise(r => setTimeout(r, 300))
        }
      }
    } catch (err) { alert('Download failed') }
    finally { setDownloading(false) }
  }"""
t = t.replace(old_batch_body, new_batch_body, 1)

# 4. Replace the batch bar with format toggle + single download button
old_bar = """        <div className="batch-bar" style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, padding: '10px 14px', background: 'var(--white)', borderRadius: 10, border: '1px solid var(--gray-200)' }}>
          <button className="btn btn-ghost btn-sm" onClick={toggleSelectAll} style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
            {completedCount > 0 && completedCount === selected.size ? <CheckSquare size={14} /> : <Square size={14} />}
            {selected.size > 0 ? `\u5df2\u9009 ${selected.size} \u9879` : '\u5168\u9009'}
          </button>
          <button className="btn btn-outline btn-sm" onClick={handleBatchDownload} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
            {downloading ? '\u6253\u5305\u4e2d..' : selected.size > 0 ? `${t.downloadZip} (${selected.size})` : t.downloadZip}
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleBatchDownloadMd} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
            {downloading ? '\u4e0b\u8f7d\u4e2d..' : selected.size > 0 ? `${t.downloadMd} (${selected.size})` : t.downloadMd}
          </button>
        </div>"""
new_bar = """        <div className="batch-bar" style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, padding: '10px 14px', background: 'var(--white)', borderRadius: 10, border: '1px solid var(--gray-200)', flexWrap: 'wrap' }}>
          <button className="btn btn-ghost btn-sm" onClick={toggleSelectAll} style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
            {completedCount > 0 && completedCount === selected.size ? <CheckSquare size={14} /> : <Square size={14} />}
            {selected.size > 0 ? `\u5df2\u9009 ${selected.size} \u9879` : '\u5168\u9009'}
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0, border: '1px solid var(--gray-200)', borderRadius: 8, overflow: 'hidden' }}>
            <button onClick={() => setDownloadFormat('md')} style={{
              padding: '5px 14px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500, fontFamily: 'inherit',
              background: downloadFormat === 'md' ? 'var(--blue)' : 'var(--white)',
              color: downloadFormat === 'md' ? 'white' : 'var(--gray-500)',
            }}>MD</button>
            <button onClick={() => setDownloadFormat('pdf')} style={{
              padding: '5px 14px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500, fontFamily: 'inherit',
              background: downloadFormat === 'pdf' ? 'var(--blue)' : 'var(--white)',
              color: downloadFormat === 'pdf' ? 'white' : 'var(--gray-500)',
            }}>PDF</button>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn btn-outline btn-sm" onClick={handleBatchDownloadZip} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
            {t.downloadZip} {selected.size > 0 && `(${selected.size})`}
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleBatchDownload} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
            {downloadFormat === 'pdf' ? 'PDF' : 'MD'} {selected.size > 0 && `(${selected.size})`}
          </button>
        </div>"""
t = t.replace(old_bar, new_bar, 1)

# 5. Replace per-item dual download buttons with single button using doDownload
old_item_btns = """                  {canView && (
                    <button className="btn btn-ghost btn-sm" style={{ padding: '4px 8px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); downloadNoteMd(item.task_id, (item.videoName || 'note').replace(/\\.[^.]+$/, '') + '.md') }}
                      title={t.downloadMd}>
                      <Download size={12} />
                    </button>
                  )}
                  {canView && (
                    <button className="btn btn-ghost btn-sm" style={{ padding: '4px 8px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); downloadNotePdf(item.task_id, (item.videoName || 'note').replace(/\\.[^.]+$/, '') + '.pdf') }}
                      title={t.downloadPdf || 'PDF'}>
                      <FileText size={12} />
                    </button>
                  )}"""
new_item_btns = """                  {canView && (
                    <button className="btn btn-ghost btn-sm" style={{ padding: '4px 8px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); doDownload(item.task_id, item.videoName) }}
                      title={downloadFormat === 'pdf' ? 'PDF' : 'MD'}>
                      <Download size={12} />
                    </button>
                  )}"""
t = t.replace(old_item_btns, new_item_btns, 1)

# 6. Update downloadNotesZip in client.js to support format param
hp.write_text(t, encoding="utf-8")
print("HistoryPage updated")

# Update client.js to pass format to zip
client = pathlib.Path(r"D:\code\video-note\frontend\src\api\client.js")
t = client.read_text(encoding="utf-8")
old_zip = """export const downloadNotesZip = async (taskIds) => {
  const response = await api.post('/notes/download-zip', taskIds, { responseType: 'blob' });"""
new_zip = """export const downloadNotesZip = async (taskIds, format) => {
  const response = await api.post('/notes/download-zip?format=' + (format || 'md'), taskIds, { responseType: 'blob' });"""
t = t.replace(old_zip, new_zip, 1)
client.write_text(t, encoding="utf-8")
print("client.js updated")
