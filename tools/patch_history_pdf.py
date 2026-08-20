import pathlib

hp_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = hp_path.read_text(encoding="utf-8")

# Update import to include downloadNotePdf
old = "import { getHistory, getHistoryAll, deleteTask, retryTask, downloadNoteMd, downloadNotesZip } from '../api/client'"
new = "import { getHistory, getHistoryAll, deleteTask, retryTask, downloadNoteMd, downloadNotePdf, downloadNotesZip } from '../api/client'"
t = t.replace(old, new, 1)

# Find the single download button and add PDF button after it
old_btn = '''                  {canView && (
                    <button className="btn btn-ghost btn-sm" style={{ padding: '4px 8px', fontSize: 12 }}
                      onClick={(e) => { e.stopPropagation(); downloadNoteMd(item.task_id, (item.videoName || 'note').replace(/\\.[^.]+$/, '') + '.md') }}
                      title={t.downloadMd}>
                      <Download size={12} />
                    </button>
                  )}'''
new_btn = '''                  {canView && (
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
                  )}'''
t = t.replace(old_btn, new_btn, 1)

# Add FileText to import if not already there
if 'FileText' not in t:
    old_import = "import { Trash2, RefreshCw, Loader2"
    new_import = "import { Trash2, RefreshCw, Loader2, FileText"
    t = t.replace(old_import, new_import, 1)

hp_path.write_text(t, encoding="utf-8")
print("HistoryPage PDF button added")
