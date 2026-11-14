import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
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
      signalAuthFailure()
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

// ── Upload ──
export const uploadVideo = async (file, onProgress, language = 'zh', noteStyle = 'standard', processingOptions = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('language', language);
  formData.append('note_style', noteStyle);
  formData.append('processing_options', JSON.stringify(processingOptions));
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => { if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total)); }
  });
  return response.data;
};

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

// ── Polish ──
export const polishNote = async (taskId, style, extraInstructions) => {
  return (await api.post('/note/' + taskId + '/polish', { style, extra_instructions: extraInstructions })).data;
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

// ── Flashcards ──
export const generateFlashcards = async (taskId, count = 8) => {
  return (await api.post('/note/' + taskId + '/flashcards', { count })).data;
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
export const getRagSessions = async (limit = 50) => (await api.get('/rag/sessions', { params: { limit } })).data;
export const getRagSession = async (sessionId) => (await api.get('/rag/sessions/' + sessionId)).data;
export const renameRagSession = async (sessionId, title) =>
  (await api.patch('/rag/sessions/' + sessionId, { title })).data;
export const deleteRagSession = async (sessionId) =>
  (await api.delete('/rag/sessions/' + sessionId)).data;


// -- Settings --
export const getSettings = async () => { return (await api.get('/settings')).data; };
export const updateSettings = async (patch) => { return (await api.put('/settings', patch)).data; };

// -- Authentication --
export const getAuthStatus = async () => (await api.get('/auth/me')).data;
export const login = async (password) => (await api.post('/auth/login', { password })).data;
export const logout = async () => (await api.post('/auth/logout')).data;

// -- Providers --
export const getProviders = async () => { return (await api.get('/providers')).data; };
export const addProvider = async (provider) => { return (await api.post('/providers', provider)).data; };
export const updateProvider = async (id, patch) => { return (await api.put('/providers/' + id, patch)).data; };
export const deleteProvider = async (id) => { return (await api.delete('/providers/' + id)).data; };
export const activateProvider = async (id) => { return (await api.post('/providers/' + id + '/activate')).data; };


export const downloadNoteHtml = async (taskId, filename) =>
  downloadBlob('/note/' + taskId + '/html', filename || 'note.html', 'text/html');

export default api;
