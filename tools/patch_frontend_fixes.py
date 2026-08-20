import pathlib

# ===== 1. Upload dedup - redirect to existing note =====
up_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\UploadPage.jsx")
t = up_path.read_text(encoding="utf-8")

# Update go function to handle already_completed
old_go = '''      try {
        const res = await uploadVideo(f, ()=>{}, lang, noteStyle)
        results.push({ ...res, fileName: f.name, fileSize: f.size, status: 'pending', progress: 0 })
      } catch(e) {
        results.push({ fileName: f.name, fileSize: f.size, error: e.message, status: 'failed', progress: 0 })
      }'''
new_go = '''      try {
        const res = await uploadVideo(f, ()=>{}, lang, noteStyle)
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
      }'''
t = t.replace(old_go, new_go, 1)

up_path.write_text(t, encoding="utf-8")
print("Upload dedup redirect done")

# ===== 2. Error handling improvements =====
# Fix silent catch blocks in UploadPage
t = up_path.read_text(encoding="utf-8")
old_catch = "getHistoryAll().then(setHistory).catch(() => {})"
new_catch = "getHistoryAll().then(setHistory).catch(err => console.warn('Failed to load history:', err))"
t = t.replace(old_catch, new_catch, 1)
up_path.write_text(t, encoding="utf-8")
print("UploadPage error handling improved")

# Fix NotePage
np_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\NotePage.jsx")
t = np_path.read_text(encoding="utf-8")
old_catch = "getHistoryAll().then(list => setNotes(list.filter(i => i.status === 'completed'))).catch(() => {})"
new_catch = "getHistoryAll().then(list => setNotes(list.filter(i => i.status === 'completed'))).catch(err => console.warn('Failed to load notes:', err))"
t = t.replace(old_catch, new_catch, 1)
np_path.write_text(t, encoding="utf-8")
print("NotePage error handling improved")

# ===== 3. Batch download confirmation =====
hp_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = hp_path.read_text(encoding="utf-8")

# Add confirmation to batch download
old_batch = "  const handleBatchDownload = async () => {\n    if (!selected.size) return"
new_batch = "  const handleBatchDownload = async () => {\n    if (!selected.size) return\n    if (!confirm(t.confirmDownload || `Download ${selected.size} notes as ZIP?`)) return"
t = t.replace(old_batch, new_batch, 1)

old_batch_md = "  const handleBatchDownloadMd = async () => {\n    if (!selected.size) return"
new_batch_md = "  const handleBatchDownloadMd = async () => {\n    if (!selected.size) return\n    if (!confirm(t.confirmDownloadMd || `Download ${selected.size} notes as MD files?`)) return"
t = t.replace(old_batch_md, new_batch_md, 1)

hp_path.write_text(t, encoding="utf-8")
print("Batch download confirmation done")

# Add translation keys
lang_path = pathlib.Path(r"D:\code\video-note\frontend\src\context\LangContext.jsx")
t = lang_path.read_text(encoding="utf-8")

# Add to zh section (after downloadAll)
old_zh = "downloadAll: '\u6279\u91cf\u4e0b\u8f7d',"
new_zh = "downloadAll: '\u6279\u91cf\u4e0b\u8f7d', confirmDownload: '\u786e\u8ba4\u4e0b\u8f7d ZIP\uff1f', confirmDownloadMd: '\u786e\u8ba4\u4e0b\u8f7d MD \u6587\u4ef6\uff1f', cancel: '\u53d6\u6d88', cancelFailed: '\u53d6\u6d88\u5931\u8d25', settings: '\u8bbe\u7f6e',"
t = t.replace(old_zh, new_zh, 1)

# Add to en section
old_en = "downloadAll: 'Batch Download',"
new_en = "downloadAll: 'Batch Download', confirmDownload: 'Download as ZIP?', confirmDownloadMd: 'Download as MD files?', cancel: 'Cancel', cancelFailed: 'Cancel failed', settings: 'Settings',"
t = t.replace(old_en, new_en, 1)

lang_path.write_text(t, encoding="utf-8")
print("Translation keys added")
