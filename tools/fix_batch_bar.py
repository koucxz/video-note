import pathlib

hp = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = hp.read_text(encoding="utf-8")

# Replace the old batch bar with new one containing format toggle
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
          <div style={{ display: 'flex', alignItems: 'center', border: '1px solid var(--gray-200)', borderRadius: 8, overflow: 'hidden' }}>
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

if old_bar in t:
    t = t.replace(old_bar, new_bar, 1)
    print("batch bar replaced")
else:
    print("old bar not found, trying alternative")
    # Try line-by-line replacement
    lines = t.split('\n')
    start = None
    end = None
    for i, line in enumerate(lines):
        if 'batch-bar' in line:
            start = i
        if start and i > start and line.strip() == '</div>' and '</div>' in lines[i-1]:
            end = i
            break
    if start and end:
        new_lines = lines[:start]
        new_lines.extend(new_bar.strip().split('\n'))
        new_lines.extend(lines[end+1:])
        t = '\n'.join(new_lines)
        print("batch bar replaced via line splice")

# Also remove the old handleBatchDownloadMd function if it exists
old_fn = """  const handleBatchDownloadMd = async () => {
    if (!selected.size) return
    if (!confirm(t.confirmDownloadMd || `Download ${selected.size} notes as MD files?`)) return
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
if old_fn in t:
    t = t.replace(old_fn, "", 1)
    print("old handleBatchDownloadMd removed")

hp.write_text(t, encoding="utf-8")
print("done")
