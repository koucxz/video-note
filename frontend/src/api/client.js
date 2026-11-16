import axios from 'axios';

export const API_BASE = (import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

const TOKEN_KEY = 'videonote_token'
export const getToken = () => {
  try { return localStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
}
export const setToken = (token) => {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {}
}
export const clearToken = () => {
  try { localStorage.removeItem(TOKEN_KEY) } catch {}
}

const api = axios.create({
  baseURL: API_BASE + '/api',
  timeout: 300000,
  withCredentials: true,
});

let _toast = null
export function setToastHandler(t) { _toast = t }

let _authFailureSignaled = false
const _noticeTimes = new Map()
const NOTICE_DEDUPE_MS = 2500

export function resetAuthFailure() {
  _authFailureSignaled = false
}

const errorMessage = (error) => {
  let msg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error'
  if (Array.isArray(msg)) msg = msg.map(e => e.msg || JSON.stringify(e)).join('; ')
  if (typeof msg === 'object') msg = JSON.stringify(msg)
  return String(msg)
}

const isAuthEndpoint = (url = '') => /\/auth\/(me|login|logout)(?:\?|$)/.test(url)

const signalAuthFailure = () => {
  if (_authFailureSignaled) return
  _authFailureSignaled = true
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('vn-unauthorized', { detail: { expired: true } }))
  }
}

const notifyErrorOnce = (error) => {
  if (!_toast || error.response?.status === 404) return
  const status = error.response?.status
  const msg = errorMessage(error)
  const key = `${status || 'network'}:${msg}`
  const now = Date.now()
  const previous = _noticeTimes.get(key) || 0
  if (now - previous < NOTICE_DEDUPE_MS) return
  _noticeTimes.set(key, now)
  for (const [noticeKey, timestamp] of _noticeTimes) {
    if (now - timestamp > NOTICE_DEDUPE_MS * 2) _noticeTimes.delete(noticeKey)
  }
  if (status >= 500) _toast.error(msg, 'Server Error')
  else if (status === 429) _toast.error(msg, 'Rate Limited')
  else if (status >= 400) _toast.info(msg)
  else if (!error.response) _toast.error('Network unreachable', 'Connection Error')
}

const readCookie = (name) => document.cookie
  .split('; ')
  .find((row) => row.startsWith(name + '='))
  ?.split('=').slice(1).join('=') || ''

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers['Authorization'] = 'Bearer ' + token
  const method = (config.method || 'get').toUpperCase()
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && !config.url?.endsWith('/auth/login')) {
    const csrf = readCookie('vn_csrf')
    if (csrf) config.headers['X-CSRF-Token'] = csrf
  }
  return config
})

api.interceptors.response.use(
  response => response,
  async error => {
    const msg = errorMessage(error)
    const status = error.response?.status
    const original = error.config
    const suppressNotice = Boolean(original?._vnSuppressErrorNotice)

    const authRequired = msg === 'Authentication required' || (status === 401 && !isAuthEndpoint(original?.url))
    if (authRequired) {
      clearToken()
      signalAuthFailure()
      return Promise.reject(error)
    }

    // Token mode is CSRF-exempt server-side; failing fast avoids a pointless
    // /auth/me + retry loop if a 403 ever leaks through.
    if (status === 403 && msg === 'CSRF validation failed' && original && getToken()) {
      return Promise.reject(error)
    }

    if (
      status === 403 &&
      msg === 'CSRF validation failed' &&
      original &&
      !original._csrfRetried &&
      !isAuthEndpoint(original.url)
    ) {
      original._csrfRetried = true
      original._vnSuppressErrorNotice = true
      try {
        const auth = await api.get('/auth/me')
        if (auth.data?.authenticated === false) {
          signalAuthFailure()
          return Promise.reject(error)
        }
        return await api.request(original)
      } catch (retryError) {
        const retryStatus = retryError.response?.status
        if (retryStatus === 401 || retryStatus === 403) signalAuthFailure()
        else notifyErrorOnce(retryError)
        return Promise.reject(retryError)
      }
    }

    if (status === 403 && msg === 'CSRF validation failed' && original?._csrfRetried) {
      signalAuthFailure()
      return Promise.reject(error)
    }

    if (!suppressNotice) notifyErrorOnce(error)
    return Promise.reject(error)
  }
);

// ── Background job polling ──
// Mutating endpoints (polish/flashcards) now return a job id immediately;
// state lives in the shared DB so any worker can answer the poll.
const pollJob = async (jobId) => {
  for (let attempt = 0; attempt < 180; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 1000))
    const response = await api.get('/jobs/' + jobId)
    const job = response.data?.data || response.data
    if (!job) throw new Error('Background job disappeared')
    if (job.status === 'done') return job.result || {}
    if (job.status === 'failed') {
      const message = job.error || 'Background job failed'
      if (_toast) _toast.error(message, 'Server Error')
      throw new Error(message)
    }
  }
  throw new Error('Background job timed out')
}

// ── Upload（分片） ──
// 单个请求传 2GB 要撑五分钟：撞前端超时、断一次从 0 重来、服务端还得先把整个
// body 落到临时文件才能校验。这里只放四个底层调用，编排逻辑在 lib/uploader.js，
// 这样上传可以在页面之外继续跑，也能按 upload_id 续传。
export const UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024

export const initUpload = async (payload) => (await api.post('/upload/init', payload)).data
export const getUploadStatus = async (uploadId) => (await api.get('/upload/' + uploadId)).data
export const completeUpload = async (uploadId) => (await api.post(`/upload/${uploadId}/complete`, null, { timeout: 300000 })).data
export const abortUpload = async (uploadId) => {
  try { await api.delete('/upload/' + uploadId) } catch { /* 会话可能已被清理 */ }
}
export const putUploadPart = async (uploadId, index, blob) => {
  const res = await api.put(`/upload/${uploadId}/part/${index}`, blob, {
    headers: { 'Content-Type': 'application/octet-stream' },
    timeout: 180000,
    transformRequest: [(d) => d],
  })
  return res.data
}

// ── Task ──
export const getTaskStatus = async (taskId) => { return (await api.get('/task/' + taskId + '/status')).data; };
export const retryTask = async (taskId) => { return (await api.post('/task/' + taskId + '/retry')).data; };
export const cancelTask = async (taskId) => { return (await api.post('/task/' + taskId + '/cancel')).data; };
export const renameTask = async (taskId, name) => { return (await api.patch('/task/' + taskId + '/name', { name })).data; };
export const deleteTask = async (taskId) => { return (await api.delete('/task/' + taskId)).data; };
export const deleteTasks = async (taskIds) => { return (await api.post('/tasks/batch-delete', { task_ids: taskIds })).data; };
export const pauseTask = async (taskId) => { return (await api.post('/task/' + taskId + '/pause')).data; };
export const resumeTask = async (taskId) => { return (await api.post('/task/' + taskId + '/resume')).data; };

// ── History ──
export const getHistory = async (page = 1, size = 20, search = '') => {
  const resp = (await api.get('/history', { params: { page, size, search } })).data;
  if (Array.isArray(resp)) return { items: resp, total: resp.length, page: 1, size: resp.length, pages: 1 };
  return resp;
};
export const getHistoryAll = async () => {
  let all = [];
  let page = 1;
  const size = 100;
  while (true) {
    const resp = await getHistory(page, size);
    const items = resp.items || [];
    all = all.concat(items);
    if (all.length >= (resp.total || 0) || items.length < size) break;
    page++;
  }
  return all;
};

// ── Note Content ──
export const getNoteStyles = async () => { return (await api.get('/note-styles')).data.styles; };
export const getNoteContent = async (taskId) => { return (await api.get('/note/' + taskId + '/content')).data; };

// ── Note Versions ──
export const getNoteVersions = async (taskId) => { return (await api.get('/note/' + taskId + '/versions')).data; };
export const getNoteVersion = async (taskId, versionId) => { return (await api.get('/note/' + taskId + '/version/' + versionId)).data; };
export const editNote = async (taskId, content) => { return (await api.post('/note/' + taskId + '/edit', { content })).data; };
export const deleteNoteVersion = async (taskId, versionId) => { return (await api.delete('/note/' + taskId + '/version/' + versionId)).data; };
export const revertNoteVersion = async (taskId, versionId) => { return (await api.post('/note/' + taskId + '/revert/' + versionId)).data; };

// ── Polish (queued) ──
// Keeps the old return shape ({ task_id, version }) so noteStore/NotePage
// keep working unchanged; the polling is hidden inside the client.
export const polishNote = async (taskId, style, extraInstructions) => {
  const started = (await api.post('/note/' + taskId + '/polish', { style, extra_instructions: extraInstructions })).data;
  const jobId = started?.data?.job_id || started?.job_id
  if (!jobId) return started
  return pollJob(jobId)
};

const downloadBlob = async (path, filename, mimeType) => {
  const response = await api.get(path, { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([response.data], { type: mimeType }));
  const a = document.createElement('a'); a.href = url;
  a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 0);
};

// ── Download ──
export const downloadNoteMd = async (taskId, filename) =>
  downloadBlob('/note/' + taskId, filename || 'note.md', 'text/markdown');

export const downloadNotePdf = async (taskId, filename) =>
  downloadBlob('/note/' + taskId + '/pdf', filename || 'note.pdf', 'application/pdf');

export const downloadNoteWord = async (taskId, filename) =>
  downloadBlob('/note/' + taskId + '/word', filename || 'note.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');

export const downloadNotesZip = async (taskIds, format) => {
  const response = await api.post('/notes/download-zip?format=' + (format || 'md'), taskIds, { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([response.data]));
  const a = document.createElement('a'); a.href = url;
  a.download = 'videonote-notes.zip';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

// ── Flashcards (queued) ──
// Returns { cards: [...] } exactly like before, so FlashcardPage is unchanged.
export const generateFlashcards = async (taskId, count = 8) => {
  const started = (await api.post('/note/' + taskId + '/flashcards', { count })).data;
  const jobId = started?.data?.job_id || started?.job_id
  if (!jobId) return started
  return pollJob(jobId)
};

// ── Favorites ──
export const toggleFavorite = async (taskId) => { return (await api.post('/favorites/' + taskId)).data; };
export const getFavorites = async () => { return (await api.get('/favorites')).data; };

// ── RAG Q&A ──
export const ragAsk = async (question, history = [], scope = {}, sessionId = null) => {
  return (await api.post('/rag/ask', {
    question,
    history,
    scope,
    ...(sessionId ? { session_id: sessionId } : {}),
  })).data;
};

// ── Streaming RAG (SSE) ──
// Reads the SSE stream with fetch/ReadableStream (axios cannot stream the
// response body). Resolves with the `done` payload, which is intentionally
// identical in shape to ragAsk's response. Throws on HTTP/CSRF/auth errors
// or an `error` event so the caller can fall back to ragAsk.
export const ragAskStream = async (payload, onDelta = null) => {
  const headers = { 'Content-Type': 'application/json' }
  const csrf = readCookie('vn_csrf')
  if (csrf) headers['X-CSRF-Token'] = csrf
  const token = getToken()
  if (token) headers['Authorization'] = 'Bearer ' + token
  const response = await fetch(API_BASE + '/api/rag/ask/stream', {
    method: 'POST',
    credentials: 'include',
    headers,
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    let detail = 'Stream request failed'
    try {
      const body = await response.json()
      detail = body?.detail || body?.message || detail
    } catch {}
    throw new Error(detail)
  }
  if (!response.body) throw new Error('Streaming not supported by this browser')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let doneData = null
  let streamError = null
  let finished = false
  while (!finished) {
    const { value, done } = await reader.read()
    finished = done
    buffer += decoder.decode(value || new Uint8Array(), { stream: !finished })
    let boundary
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      let event = 'message'
      let data = ''
      for (const line of frame.split(/\r?\n/)) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data += line.slice(5).trim()
      }
      if (!data) continue
      let parsed
      try { parsed = JSON.parse(data) } catch { continue }
      if (event === 'delta') onDelta?.(parsed)
      else if (event === 'done') doneData = parsed
      else if (event === 'error') streamError = parsed
    }
  }
  if (streamError) throw new Error(streamError.error || 'Stream error')
  if (!doneData) throw new Error('Stream ended before completion')
  return doneData
};
export const getRagSessions = async (limit = 50) => (await api.get('/rag/sessions', { params: { limit } })).data;
export const getRagSession = async (sessionId) => (await api.get('/rag/sessions/' + sessionId)).data;
export const renameRagSession = async (sessionId, title) =>
  (await api.patch('/rag/sessions/' + sessionId, { title })).data;
export const deleteRagSession = async (sessionId) =>
  (await api.delete('/rag/sessions/' + sessionId)).data;


// -- Settings --
export const getSettings = async () => { return (await api.get('/settings')).data; };
export const getTokenUsage = async (days = 7) => { return (await api.get('/usage/tokens', { params: { days } })).data; };
export const updateSettings = async (patch) => { return (await api.put('/settings', patch)).data; };

// -- Authentication --
export const getAuthStatus = async () => (await api.get('/auth/me')).data;
export const login = async (username, password) => (await api.post('/auth/login', { username, password })).data;
export const logout = async () => {
  const data = (await api.post('/auth/logout')).data;
  clearToken();
  return data;
};

// -- Providers --
export const getProviders = async () => { return (await api.get('/providers')).data; };
export const addProvider = async (provider) => { return (await api.post('/providers', provider)).data; };
export const updateProvider = async (id, patch) => { return (await api.put('/providers/' + id, patch)).data; };
export const deleteProvider = async (id) => { return (await api.delete('/providers/' + id)).data; };
export const activateProvider = async (id) => { return (await api.post('/providers/' + id + '/activate')).data; };


export const downloadNoteHtml = async (taskId, filename) =>
  downloadBlob('/note/' + taskId + '/html', filename || 'note.html', 'text/html');

export default api;
