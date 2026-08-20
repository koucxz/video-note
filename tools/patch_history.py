import pathlib
p = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = p.read_text(encoding="utf-8")

# 1. Update import
old_imp = "import { getHistory, deleteTask, retryTask, downloadNotesZip } from '../api/client'"
new_imp = "import { getHistory, deleteTask, retryTask, downloadNoteMd, downloadNotesZip } from '../api/client'"
t = t.replace(old_imp, new_imp)

# 2. Add single download button for completed items - add after the ArrowUpRight button
old_btn = """                  {canView && (
                    <button className=\"btn btn-primary btn-sm\" style={{ padding: '4px 10px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); navigate(`/note/${item.task_id}`) }}>
                      <ArrowUpRight size={12} /> {t.view}
                    </button>
                  )}"""
new_btn = """                  {canView && (
                    <button className=\"btn btn-primary btn-sm\" style={{ padding: '4px 10px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); navigate(`/note/${item.task_id}`) }}>
                      <ArrowUpRight size={12} /> {t.view}
                    </button>
                  )}
                  {canView && (
                    <button className=\"btn btn-ghost btn-sm\" style={{ padding: '4px 8px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); downloadNoteMd(item.task_id, (item.videoName || 'note').replace(/\\.[^.]+$/, '') + '.md') }}
                      title={t.downloadMd}>
                      <Download size={12} />
                    </button>
                  )}"""
t = t.replace(old_btn, new_btn)

# 3. Add batch download MD button after the ZIP button
old_zip = """          <button className=\"btn btn-primary btn-sm\" onClick={handleBatchDownload} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className=\"spin\" /> : <Download size={14} />}
            {downloading ? '\u6253\u5305\u4e2d..' : selected.size > 0 ? `\u4e0b\u8f7d ZIP (${selected.size})` : '\u4e0b\u8f7d ZIP'}
          </button>"""
new_zip = """          <button className=\"btn btn-outline btn-sm\" onClick={handleBatchDownload} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className=\"spin\" /> : <Download size={14} />}
            {downloading ? '\u6253\u5305\u4e2d..' : selected.size > 0 ? `${t.downloadZip} (${selected.size})` : t.downloadZip}
          </button>
          <button className=\"btn btn-primary btn-sm\" onClick={handleBatchDownloadMd} disabled={!selected.size || downloading}>
            {downloading ? <Loader2 size={14} className=\"spin\" /> : <Download size={14} />}
            {downloading ? '\u4e0b\u8f7d\u4e2d..' : selected.size > 0 ? `${t.downloadMd} (${selected.size})` : t.downloadMd}
          </button>"""
t = t.replace(old_zip, new_zip)

# 4. Add the batch download MD handler after handleBatchDownload
old_handler_end = """    finally { setDownloading(false) }
  }"""
# Find the second occurrence (after handleBatchDownload)
idx = t.find(old_handler_end)
if idx > 0:
    insert = """

  const handleBatchDownloadMd = async () => {
    if (!selected.size) return
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
    } catch (err) { alert('\u4e0b\u8f7d\u5931\u8d25') }
    finally { setDownloading(false) }
  }"""
    t = t[:idx+len(old_handler_end)] + insert + t[idx+len(old_handler_end):]

p.write_text(t, encoding="utf-8")
print("done")
