import pathlib

up_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\UploadPage.jsx")
t = up_path.read_text(encoding="utf-8")

# Add import
old = "import { uploadVideo, getHistoryAll, getTaskStatus, retryTask } from '../api/client'"
new = "import { uploadVideo, getHistoryAll, getTaskStatus, retryTask } from '../api/client'\nimport { useGlobalWebSocket } from '../hooks/useWebSocket'"
t = t.replace(old, new, 1)

# Add WebSocket hook
old_state = "  const ref = useRef(null)"
new_state = "  const ref = useRef(null)\n  const wsUpdates = useGlobalWebSocket()"
t = t.replace(old_state, new_state, 1)

# Add WebSocket update handler
old_effect = "  useEffect(() => {\n    if (!uploadResults.length) return"
new_effect = "  // Sync WebSocket updates to upload results\n  useEffect(() => {\n    if (wsUpdates && wsUpdates.length > 0) {\n      const latest = wsUpdates[wsUpdates.length - 1];\n      setUploadResults(prev => prev.map(r => {\n        if (r.task_id === latest.task_id) {\n          return { ...r, status: latest.status, progress: latest.progress, stage: latest.stage };\n        }\n        return r;\n      }));\n    }\n  }, [wsUpdates]);\n\n  useEffect(() => {\n    if (!uploadResults.length) return"
t = t.replace(old_effect, new_effect, 1)

up_path.write_text(t, encoding="utf-8")
print("UploadPage.jsx WebSocket patched")
