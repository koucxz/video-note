import pathlib

# Update ProcessingPage to use WebSocket
pp_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\ProcessingPage.jsx")
t = pp_path.read_text(encoding="utf-8")

# Add import
old = "import { getTaskStatus, retryTask } from '../api/client'"
new = "import { getTaskStatus, retryTask, cancelTask } from '../api/client'\nimport { useTaskWebSocket } from '../hooks/useWebSocket'"
t = t.replace(old, new, 1)

# Add WebSocket hook usage after state declarations
old_state = "  const [status, setStatus] = useState(null)"
new_state = "  const [status, setStatus] = useState(null)\n  const wsStatus = useTaskWebSocket(taskId)"
t = t.replace(old_state, new_state, 1)

# Add WebSocket status sync
old_effect = "  useEffect(() => {\n    const timer = setInterval(async () => {"
new_effect = "  // Sync WebSocket updates\n  useEffect(() => {\n    if (wsStatus && wsStatus.status) {\n      setStatus(prev => ({ ...prev, ...wsStatus }));\n      if (wsStatus.status === 'completed') {\n        setTimeout(() => navigate(`/note/${taskId}`), 2000);\n      }\n    }\n  }, [wsStatus, taskId, navigate]);\n\n  // Fallback polling (slower interval)\n  useEffect(() => {\n    const timer = setInterval(async () => {"
t = t.replace(old_effect, new_effect, 1)

# Add cancel button functionality
old_retry = "  const handleManualRetry = async () => {"
new_retry = "  const handleCancel = async () => {\n    try { await cancelTask(taskId); navigate('/history'); }\n    catch (err) { alert(t.cancelFailed || 'Cancel failed'); }\n  }\n\n  const handleManualRetry = async () => {"
t = t.replace(old_retry, new_retry, 1)

# Add cancel button in the processing state UI
old_processing = '''        ) : (
          <div style={{ textAlign: 'center' }}>
            <Loader2 size={28} className="spin" color="var(--blue)" />
          </div>
        )}'''
new_processing = '''        ) : (
          <div style={{ textAlign: 'center' }}>
            <Loader2 size={28} className="spin" color="var(--blue)" />
            <button className="btn btn-ghost btn-sm" style={{ marginTop: 12 }} onClick={handleCancel}>
              {t.cancel || 'Cancel'}
            </button>
          </div>
        )}'''
t = t.replace(old_processing, new_processing, 1)

pp_path.write_text(t, encoding="utf-8")
print("ProcessingPage.jsx WebSocket patched")

# Add cancelTask to client.js
client_path = pathlib.Path(r"D:\code\video-note\frontend\src\api\client.js")
t = client_path.read_text(encoding="utf-8")

old = "export const deleteTask"
new = "export const cancelTask = async (taskId) => { return (await api.post('/task/' + taskId + '/cancel')).data; };\n\nexport const deleteTask"
t = t.replace(old, new, 1)

client_path.write_text(t, encoding="utf-8")
print("client.js cancelTask added")
