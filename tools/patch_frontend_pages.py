import pathlib

# Update UploadPage.jsx to use getHistoryAll
up_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\UploadPage.jsx")
t = up_path.read_text(encoding="utf-8")

# Update import
old = "import { uploadVideo, getHistory, getTaskStatus, retryTask } from '../api/client'"
new = "import { uploadVideo, getHistoryAll, getTaskStatus, retryTask } from '../api/client'"
t = t.replace(old, new, 1)

# Update usage
old = "getHistory().then(setHistory).catch(() => {})"
new = "getHistoryAll().then(setHistory).catch(() => {})"
t = t.replace(old, new, 1)

up_path.write_text(t, encoding="utf-8")
print("UploadPage.jsx patched")

# Update NotePage.jsx to use getHistoryAll
np_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\NotePage.jsx")
t = np_path.read_text(encoding="utf-8")

old = "import { getNoteContent, getHistory } from '../api/client'"
new = "import { getNoteContent, getHistoryAll } from '../api/client'"
t = t.replace(old, new, 1)

old = "getHistory().then(list => setNotes(list.filter(i => i.status === 'completed'))).catch(() => {})"
new = "getHistoryAll().then(list => setNotes(list.filter(i => i.status === 'completed'))).catch(() => {})"
t = t.replace(old, new, 1)

np_path.write_text(t, encoding="utf-8")
print("NotePage.jsx patched")

# Update HistoryPage.jsx to use paginated API
hp_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = hp_path.read_text(encoding="utf-8")

# Update import
old = "import { getHistory, deleteTask, retryTask, downloadNoteMd, downloadNotesZip } from '../api/client'"
new = "import { getHistory, getHistoryAll, deleteTask, retryTask, downloadNoteMd, downloadNotesZip } from '../api/client'"
t = t.replace(old, new, 1)

# Add pagination state
old = "  const [downloading, setDownloading] = useState(false)"
new = "  const [downloading, setDownloading] = useState(false)\n  const [page, setPage] = useState(1)\n  const [totalPages, setTotalPages] = useState(1)\n  const [total, setTotal] = useState(0)"
t = t.replace(old, new, 1)

# Update loadHistory to use pagination
old = """  const loadHistory = async () => {
    try { setLoading(true); setHistory(await getHistory()) }
    catch (err) { console.error(err) }
    finally { setLoading(false) }
  }"""
new = """  const loadHistory = async (p = 1) => {
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
  }"""
t = t.replace(old, new, 1)

# Update total records display
old = '<span style={{ fontSize: 13, color: \'var(--gray-400)\' }}>{t.totalRecords} {filtered.length} {t.records}</span>'
new = '<span style={{ fontSize: 13, color: \'var(--gray-400)\' }}>{t.totalRecords} {total} {t.records}</span>'
t = t.replace(old, new, 1)

# Add pagination controls before closing div
old_end = "    </div>\n  )\n}\n\nexport default HistoryPage"
new_end = """      {/* Pagination */}
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
    </div>
  )
}

export default HistoryPage"""
t = t.replace(old_end, new_end, 1)

hp_path.write_text(t, encoding="utf-8")
print("HistoryPage.jsx pagination patched")
