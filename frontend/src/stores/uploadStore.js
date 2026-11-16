/**
 * 上传任务队列（全局）。
 *
 * 之前上传状态放在 UploadPage 的 useState 里：一离开页面就全丢，只剩后台请求
 * 还在跑，回来既看不到进度也接不上。现在任务和进度都在这个 store 里，上传循环
 * 跑在 lib/uploader.js 的模块层，切页面、组件卸载都不影响；刷新页面后还能从
 * localStorage 里的 upload_id 找回断点，重新选中同一个文件就从断点继续。
 */
import { create } from 'zustand'
import { runUpload, jobKey, loadSessions, writeSession } from '../lib/uploader'

const inFlight = new Set()

const emptyJob = (file) => ({
  key: jobKey(file),
  file,
  fileName: file.name,
  fileSize: file.size,
  lastModified: file.lastModified || 0,
  status: 'queued',      // queued | uploading | finalizing | resumable | pending | processing | completed | failed
  progress: 0,
  stage: '',
  task_id: '',
  uploadId: '',
  resumed: false,
  error: '',
})

export const useUploadStore = create((set, get) => {
  const patch = (key, p) => set((s) => ({ jobs: s.jobs.map((j) => (j.key === key ? { ...j, ...p } : j)) }))

  return {
    jobs: [],
    options: { language: 'zh', note_style: 'standard', processing_options: {} },

    /** 页面挂载时调用：把上次没传完的断点显示成「可继续」的条目 */
    hydrate: () => {
      const sessions = loadSessions()
      const known = new Set(get().jobs.map((j) => j.key))
      const restored = Object.entries(sessions)
        .filter(([key]) => !known.has(key))
        .map(([key, s]) => {
          const uploaded = (s.uploadedParts || []).reduce(
            (sum, i) => sum + Math.min(s.chunkSize || 0, s.size - i * (s.chunkSize || 0)), 0)
          return {
            key,
            file: null,
            fileName: s.name,
            fileSize: s.size,
            lastModified: s.lastModified || 0,
            status: 'resumable',
            progress: s.size ? Math.min(0.99, uploaded / s.size) : 0,
            stage: '',
            task_id: '',
            uploadId: s.uploadId,
            resumed: true,
            error: '',
          }
        })
      if (restored.length) set((s) => ({ jobs: [...s.jobs, ...restored] }))
    },

    setOptions: (options) => set((s) => ({ options: { ...s.options, ...options } })),

    /** 加入待上传文件；同名同大小的断点会自动挂上 File 并继续 */
    addFiles: (fileList) => {
      const files = Array.from(fileList || [])
      if (!files.length) return []
      const resumable = new Set(
        get().jobs
          .filter((j) => (j.status === 'resumable' || (j.status === 'failed' && !j.file))
            && files.some((f) => jobKey(f) === j.key))
          .map((j) => j.key),
      )
      if (resumable.size) {
        set((s) => ({
          jobs: s.jobs.map((j) => {
            if (!resumable.has(j.key)) return j
            const file = files.find((f) => jobKey(f) === j.key)
            return { ...j, file, status: 'queued', error: '' }
          }),
        }))
      }

      const known = new Set(get().jobs.map((j) => j.key))
      const fresh = files.filter((f) => !known.has(jobKey(f))).map(emptyJob)
      if (fresh.length) set((s) => ({ jobs: [...s.jobs, ...fresh] }))

      // 断点是用户重新挑的文件，直接接着传
      resumable.forEach((key) => { get().start(key) })
      return fresh
    },

    start: async (key) => {
      const job = get().jobs.find((j) => j.key === key)
      if (!job || !job.file || inFlight.has(key)) return
      inFlight.add(key)
      patch(key, { status: 'uploading', progress: 0, error: '', stage: 'uploading' })
      try {
        const res = await runUpload({
          key,
          file: job.file,
          options: get().options,
          onStage: (stage) => patch(key, {
            status: stage === 'finalizing' ? 'finalizing' : 'uploading',
            stage,
          }),
          onProgress: (progress) => patch(key, { progress }),
          onSession: ({ uploadId, resumed }) => patch(key, { uploadId, resumed }),
        })
        if (res.already_completed) {
          patch(key, { ...res, fileName: job.fileName, status: 'completed', progress: 1 })
        } else {
          patch(key, { ...res, fileName: job.fileName, status: 'pending', progress: 0 })
        }
      } catch (err) {
        const detail = err?.response?.data?.detail || err?.message || '上传失败'
        patch(key, { status: 'failed', error: String(detail) })
      } finally {
        inFlight.delete(key)
      }
    },

    /** 顺序上传，别让多个大文件抢同一条上行带宽 */
    startAll: async (options) => {
      if (options) get().setOptions(options)
      const queued = get().jobs
        .filter((j) => j.status === 'queued' && j.file && !inFlight.has(j.key))
        .map((j) => j.key)
      for (const key of queued) await get().start(key)
    },

    /** 任务状态（WebSocket / 轮询）回写到对应的上传条目 */
    patchByTask: (taskId, p) => set((s) => ({
      jobs: s.jobs.map((j) => (j.task_id === taskId ? { ...j, ...p } : j)),
    })),

    removeJob: (key) => {
      const job = get().jobs.find((j) => j.key === key)
      if (!job) return
      if (job.uploadId) writeSession(key, null)
      set((s) => ({ jobs: s.jobs.filter((j) => j.key !== key) }))
    },

    /** 清空未在跑的条目（含排队中的选择），正在上传的不动 */
    clearSettled: () => set((s) => ({
      jobs: s.jobs.filter((j) => ['uploading', 'finalizing'].includes(j.status)),
    })),
  }
})
