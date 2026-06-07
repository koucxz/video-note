import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
});

// Global error toast handler
let _toast = null
export function setToastHandler(t) { _toast = t }

api.interceptors.response.use(
  response => response,
  error => {
    let msg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error'
    // Handle Pydantic validation error array
    if (Array.isArray(msg)) msg = msg.map(e => e.msg || JSON.stringify(e)).join('; ')
    if (typeof msg === 'object') msg = msg.msg || JSON.stringify(msg)
    const status = error.response?.status
    if (_toast && status !== 404) {
      if (status >= 500) _toast.error(msg, 'Server Error')
      else if (status === 429) _toast.error(msg, 'Rate Limited')
      else if (status >= 400) _toast.info(msg)
      else if (!error.response) _toast.error('Network unreachable', 'Connection Error')
    }
    return Promise.reject(error)
  }
);

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

export const getTaskStatus = async (taskId) => { return (await api.get('/task/' + taskId + '/status')).data; };
export const retryTask = async (taskId) => { return (await api.post('/task/' + taskId + '/retry')).data; };
export const cancelTask = async (taskId) => { return (await api.post('/task/' + taskId + '/cancel')).data; };

export const deleteTask = async (taskId) => { return (await api.delete('/task/' + taskId)).data; };
export const getHistory = async (page = 1, size = 20) => {
  const resp = (await api.get('/history', { params: { page, size } })).data;
  // Handle both paginated and legacy array response
  if (Array.isArray(resp)) return { items: resp, total: resp.length, page: 1, size: resp.length, pages: 1 };
  return resp;
};
export const getHistoryAll = async () => {
  const resp = await getHistory(1, 100);
  return resp.items || [];
};
export const getNoteContent = async (taskId) => { return (await api.get('/note/' + taskId + '/content')).data; };

export const downloadNoteMd = async (taskId, filename) => {
  const response = await api.get('/note/' + taskId, { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([response.data]));
  const a = document.createElement('a'); a.href = url;
  a.download = filename || 'note.md';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const downloadNotePdf = async (taskId, filename) => {
  const response = await api.get('/note/' + taskId + '/pdf', { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([response.data]));
  const a = document.createElement('a'); a.href = url;
  a.download = filename || 'note.pdf';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const generateFlashcards = async (taskId, count = 8) => {
  return (await api.post('/note/' + taskId + '/flashcards', { count })).data;
};

export const polishNote = async (taskId, style, extraInstructions) => {
  return (await api.post('/note/' + taskId + '/polish', { style, extra_instructions: extraInstructions })).data;
};

export const downloadNoteWord = async (taskId, filename) => {
  const response = await api.get('/note/' + taskId + '/word', { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([response.data]));
  const a = document.createElement('a'); a.href = url;
  a.download = filename || 'note.docx';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export const downloadNotesZip = async (taskIds, format) => {
  const response = await api.post('/notes/download-zip?format=' + (format || 'md'), taskIds, { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([response.data]));
  const a = document.createElement('a'); a.href = url;
  a.download = 'videonote-notes.zip';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

export default api;
