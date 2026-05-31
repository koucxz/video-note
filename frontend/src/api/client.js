import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
});

export const uploadVideo = async (file, onProgress, language = 'zh') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('language', language);
  
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total));
    }
  });
  return response.data;
};

export const getTaskStatus = async (taskId) => {
  const response = await api.get(`/task/${taskId}/status`);
  return response.data;
};

export const retryTask = async (taskId) => {
  const response = await api.post(`/task/${taskId}/retry`);
  return response.data;
};

export const deleteTask = async (taskId) => {
  const response = await api.delete(`/task/${taskId}`);
  return response.data;
};

export const getHistory = async () => {
  const response = await api.get('/history');
  return response.data;
};

export const getNoteContent = async (taskId) => {
  const response = await api.get(`/note/${taskId}/content`);
  return response.data;
};

export default api;
