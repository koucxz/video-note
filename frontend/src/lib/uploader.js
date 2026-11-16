/**
 * 分片上传编排：会话复用、并发、单块重试、按字节报进度。
 *
 * 这里刻意不依赖 React：上传循环跑在模块层，所以组件卸载、切页面都不会中断它。
 * 断点信息存 localStorage（upload_id + 已完成分片），页面刷新后重新选中同一个文件
 * 就能从服务端记录的 uploaded_parts 接着传。
 */
import {
  UPLOAD_CHUNK_SIZE, initUpload, getUploadStatus, putUploadPart, completeUpload,
} from '../api/client'

const PARALLEL = 3
const PART_RETRIES = 3
const SESSION_KEY = 'vn_upload_sessions'
const sleep = (ms) => new Promise(r => setTimeout(r, ms))

/** 文件指纹：同名同大小同修改时间视为同一个文件（用于找回断点） */
export const jobKey = (file) => `${file.name}|${file.size}|${file.lastModified || 0}`

export function loadSessions() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || '{}') || {} } catch { return {} }
}

export function writeSession(key, value) {
  const all = loadSessions()
  if (value) all[key] = value
  else delete all[key]
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(all)) } catch { /* 隐私模式下写不进去就算了 */ }
}

async function withRetry(fn) {
  let lastErr
  for (let attempt = 1; attempt <= PART_RETRIES; attempt++) {
    try {
      return await fn()
    } catch (err) {
      lastErr = err
      const status = err.response?.status
      // 4xx 除了超时/限流都不值得重试
      if (status && status >= 400 && status < 500 && status !== 408 && status !== 429) throw err
      if (attempt < PART_RETRIES) await sleep(500 * attempt)
    }
  }
  throw lastErr
}

/**
 * 跑一个文件的分片上传。
 * @returns 服务端 complete 的响应（task_id / already_completed / ...）
 */
export async function runUpload({ key, file, options = {}, onProgress, onStage, onSession }) {
  const saved = loadSessions()[key]
  let uploadId = ''
  let chunkSize = UPLOAD_CHUNK_SIZE
  let totalParts = 0
  let done = new Set()
  let resumed = false

  // 1. 有断点就先问服务端还记得哪些分片
  if (saved?.uploadId) {
    try {
      const st = await getUploadStatus(saved.uploadId)
      if (st.size === file.size) {
        uploadId = st.upload_id
        chunkSize = st.chunk_size
        totalParts = st.total_parts
        done = new Set(st.uploaded_parts || [])
        resumed = true
      }
    } catch {
      // 会话过期（12 小时）或已被清理，退回重新开始
    }
  }

  // 2. 没有可用断点就开一个新会话
  if (!uploadId) {
    let init
    try {
      init = await initUpload({
        filename: file.name,
        size: file.size,
        chunk_size: UPLOAD_CHUNK_SIZE,
        language: options.language || 'zh',
        note_style: options.note_style || 'standard',
        processing_options: JSON.stringify(options.processing_options || {}),
      })
    } catch (err) {
      writeSession(key, null)
      throw err
    }
    uploadId = init.upload_id
    chunkSize = init.chunk_size
    totalParts = init.total_parts
    done = new Set(init.uploaded_parts || [])
    writeSession(key, {
      uploadId, name: file.name, size: file.size,
      lastModified: file.lastModified || 0,
      chunkSize, totalParts, uploadedParts: [...done], updatedAt: Date.now(),
    })
  }

  const persist = () => writeSession(key, {
    uploadId, name: file.name, size: file.size,
    lastModified: file.lastModified || 0,
    chunkSize, totalParts, uploadedParts: [...done], updatedAt: Date.now(),
  })

  const sizeOf = (index) => Math.min(chunkSize, file.size - index * chunkSize)
  let uploaded = 0
  done.forEach((index) => { uploaded += sizeOf(index) })
  const total = file.size || 1
  const report = () => onProgress?.(Math.min(0.99, uploaded / total))

  onSession?.({ uploadId, resumed, uploadedParts: [...done] })
  onStage?.(resumed && done.size ? 'resuming' : 'uploading')
  report()

  // 3. 只补缺失的分片，3 路并发
  const queue = []
  for (let i = 0; i < totalParts; i++) if (!done.has(i)) queue.push(i)

  let cursor = 0
  const worker = async () => {
    while (cursor < queue.length) {
      const index = queue[cursor++]
      const start = index * chunkSize
      const blob = file.slice(start, Math.min(start + chunkSize, file.size))
      await withRetry(() => putUploadPart(uploadId, index, blob))
      done.add(index)
      uploaded += blob.size
      persist()
      report()
    }
  }
  await Promise.all(Array.from({ length: Math.min(PARALLEL, queue.length) }, worker))

  // 4. 合并 + 建任务
  onStage?.('finalizing')
  onProgress?.(0.995)
  const res = await completeUpload(uploadId)
  writeSession(key, null)
  onProgress?.(1)
  return res
}
