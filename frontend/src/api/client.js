import axios from 'axios';

// API base: 本地 dev 留空 -> 走 vite proxy 的 /api；生产在 Vercel 配 VITE_API_BASE_URL 指向后端
const _RAW_BASE = import.meta.env.VITE_API_BASE_URL || '';
const _BASE = _RAW_BASE.replace(/\/+$/, '');
const _TOKEN = import.meta.env.VITE_API_TOKEN || '';

const api = axios.create({
  baseURL: _BASE ? `${_BASE}/api` : '/api',
  timeout: 300000,
  headers: _TOKEN ? { 'X-VN-Token': _TOKEN } : {},
});

// ── 登录态 ──
const TOKEN_KEY = 'vn_auth_token';
export const getToken = () => {
  try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; }
};
export const setAuthToken = (t) => {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ }
};
export const clearAuthToken = () => setAuthToken('');

api.interceptors.request.use((config) => {
  const t = getToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

let _toast = null
export function setToastHandler(t) { _toast = t }

api.interceptors.response.use(
  response => response,
  error => {
    let msg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error'
    if (Array.isArray(msg)) msg = msg.map(e => e.msg || JSON.stringify(e)).join('; ')
    if (typeof msg === 'object') msg = JSON.stringify(msg)
    msg = String(msg)
    const status = error.response?.status
    if (status === 401 && !error.config?.url?.includes('/auth/login')) {
      clearAuthToken()
      window.dispatchEvent(new CustomEvent('vn-unauthorized'))
    }
    if (_toast && status !== 404) {
      if (status >= 500) _toast.error(msg, 'Server Error')
      else if (status === 429) _toast.error(msg, 'Rate Limited')
      else if (status >= 400 && status !== 401) _toast.info(msg)
      else if (!error.response) _toast.error('Network unreachable', 'Connection Error')
    }
    return Promise.reject(error)
  }
);

// ── Auth（单用户登录，无注册） ──
export const getAuthConfig = async () => (await api.get('/auth/config')).data;
export const login = async (username, password) => (await api.post('/auth/login', { username, password })).data;
export const fetchMe = async () => (await api.get('/auth/me')).data;


// ── Upload ──
// 小文件单次上传；大文件自动切片（支持断点续传、并发分片、失败重传）
const CHUNK_SIZE = 2 * 1024 * 1024;        // 2MB / 片
const CHUNK_CONCURRENCY = 3;               // 并发上传片数
const CHUNK_THRESHOLD = 8 * 1024 * 1024;   // 超过 8MB 走切片

const singleUpload = async (file, onProgress, language, noteStyle, processingOptions) => {
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

const chunkedUpload = async (file, onProgress, language, noteStyle, processingOptions) => {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  const init = (await api.post('/upload/init', {
    filename: file.name,
    size: file.size,
    chunk_size: CHUNK_SIZE,
    total_chunks: totalChunks,
  })).data;

  const uploadId = init.upload_id;
  const chunkSize = init.chunk_size || CHUNK_SIZE;
  const total = init.total_chunks || totalChunks;
  const done = new Set(init.uploaded || []);

  let sentBytes = 0;
  done.forEach((i) => {
    sentBytes += Math.min(chunkSize, file.size - i * chunkSize);
  });
  const emit = () => onProgress?.(Math.min(99, Math.round((sentBytes / file.size) * 100)));
  emit();

  const sendOne = async (i) => {
    const start = i * chunkSize;
    const blob = file.slice(start, Math.min(start + chunkSize, file.size));
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const fd = new FormData();
        fd.append('upload_id', uploadId);
        fd.append('index', String(i));
        fd.append('chunk', blob, `chunk-${i}`);
        await api.post('/upload/chunk', fd, { timeout: 120000 });
        sentBytes += blob.size;
        emit();
        return;
      } catch (err) {
        if (attempt === 2) throw err;
        await new Promise((r) => setTimeout(r, 800 * (attempt + 1)));
      }
    }
  };

  const queue = [];
  for (let i = 0; i < total; i++) if (!done.has(i)) queue.push(i);

  const workers = Array.from(
    { length: Math.max(1, Math.min(CHUNK_CONCURRENCY, queue.length)) },
    async () => {
      while (queue.length) {
        const idx = queue.shift();
        await sendOne(idx);
      }
    }
  );
  await Promise.all(workers);

  onProgress?.(100);
  const res = await api.post('/upload/complete', {
    upload_id: uploadId,
    language,
    note_style: noteStyle,
    processing_options: JSON.stringify(processingOptions || {}),
  }, { timeout: 600000 });
  return res.data;
};

export const uploadVideo = async (file, onProgress, language = 'zh', noteStyle = 'standard', processingOptions = {}) => {
  if (file.size > CHUNK_THRESHOLD) {
    return chunkedUpload(file, onProgress, language, noteStyle, processingOptions);
  }
  return singleUpload(file, onProgress, language, noteStyle, processingOptions);
};

// ── Task ──
export const getTaskStatus = async (taskId) => { return (await api.get('/task/' + taskId + '/status')).data; };
export const retryTask = async (taskId) => { return (await api.post('/task/' + taskId + '/retry')).data; };
export const cancelTask = async (taskId) => { return (await api.post('/task/' + taskId + '/cancel')).data; };
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

// ── Collections ──
export const getCollections = async () => { return (await api.get('/collections')).data; };
export const createCollection = async (data) => { return (await api.post('/collections', data)).data; };
export const updateCollection = async (colId, data) => { return (await api.put('/collections/' + colId, data)).data; };
export const deleteCollection = async (colId) => { return (await api.delete('/collections/' + colId)).data; };
export const addToCollection = async (colId, noteId) => { return (await api.post('/collections/' + colId + '/notes/' + noteId)).data; };
export const removeFromCollection = async (colId, noteId) => { return (await api.delete('/collections/' + colId + '/notes/' + noteId)).data; };
export const getCollectionNotes = async (colId) => { return (await api.get('/collections/' + colId + '/notes')).data; };

// ── Favorites ──
export const toggleFavorite = async (taskId) => { return (await api.post('/favorites/' + taskId)).data; };
export const getFavorites = async () => { return (await api.get('/favorites')).data; };

// ── RAG Q&A ──
export const ragAsk = async (question, history = [], scope = {}) => {
  return (await api.post('/rag/ask', { question, history, scope })).data;
};


// -- Settings --
export const getSettings = async () => { return (await api.get('/settings')).data; };
export const updateSettings = async (patch) => { return (await api.put('/settings', patch)).data; };

// -- Providers --
export const getProviders = async () => { return (await api.get('/providers')).data; };
export const addProvider = async (provider) => { return (await api.post('/providers', provider)).data; };
export const updateProvider = async (id, patch) => { return (await api.put('/providers/' + id, patch)).data; };
export const deleteProvider = async (id) => { return (await api.delete('/providers/' + id)).data; };
export const activateProvider = async (id) => { return (await api.post('/providers/' + id + '/activate')).data; };


export const downloadNoteHtml = async (taskId, filename) =>
  downloadBlob('/note/' + taskId + '/html', filename || 'note.html', 'text/html');

export default api;
