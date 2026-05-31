import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileVideo, Loader2, X, Plus, Globe } from 'lucide-react'
import { uploadVideo } from '../api/client'

function UploadPage() {
  const [files, setFiles] = useState([])
  const [language, setLanguage] = useState('zh')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()

  const addFiles = useCallback((newFiles) => {
    const videoFiles = Array.from(newFiles).filter(f => 
      /\.(mp4|avi|mov|mkv|wmv|flv|webm|m4v)$/i.test(f.name)
    )
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name + f.size))
      const unique = videoFiles.filter(f => !existing.has(f.name + f.size))
      return [...prev, ...unique]
    })
  }, [])

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleDrop = (e) => {
    e.preventDefault()
    addFiles(e.dataTransfer.files)
  }

  const handleUploadAll = async () => {
    if (files.length === 0) return
    setUploading(true)
    
    const results = []
    for (const file of files) {
      try {
        const result = await uploadVideo(file, () => {}, language)
        results.push({ ...result, filename: file.name })
      } catch (err) {
        results.push({ filename: file.name, error: err.message })
      }
    }
    
    setUploading(false)
    
    if (results.length === 1 && results[0].task_id) {
      navigate(`/processing/${results[0].task_id}`)
    } else {
      navigate('/history')
    }
  }

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', marginBottom: '8px' }}>
          上传视频
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '15px' }}>
          支持 MP4, AVI, MOV, MKV 等格式，可同时上传多个
        </p>
      </div>

      {/* 语言选择 */}
      <div className="card" style={{ marginBottom: '16px', padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Globe size={20} color="var(--primary)" />
          <span style={{ fontWeight: '500', fontSize: '14px' }}>输出语言</span>
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className={`btn ${language === 'zh' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '8px 20px' }}
              onClick={() => setLanguage('zh')}
            >
              中文
            </button>
            <button
              className={`btn ${language === 'en' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '8px 20px' }}
              onClick={() => setLanguage('en')}
            >
              English
            </button>
          </div>
        </div>
      </div>

      {/* 拖拽区域 */}
      <div
        className="card"
        style={{
          border: '2px dashed var(--border)',
          textAlign: 'center',
          padding: '40px',
          cursor: 'pointer',
          transition: 'all 0.2s',
          background: files.length > 0 ? 'var(--bg)' : 'var(--card-bg)'
        }}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          multiple
          onChange={(e) => addFiles(e.target.files)}
          style={{ display: 'none' }}
        />
        
        <div style={{
          width: 56, height: 56, borderRadius: 16, background: 'var(--primary-light)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px'
        }}>
          <Plus size={28} color="var(--primary)" />
        </div>
        <p style={{ fontWeight: '500', marginBottom: '4px' }}>点击或拖拽视频文件到此处</p>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>可以一次选择多个文件</p>
      </div>

      {/* 文件列表 */}
      {files.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontWeight: '500', fontSize: '14px' }}>已选择 {files.length} 个文件</span>
            <button className="btn btn-secondary" style={{ fontSize: '13px', padding: '6px 12px' }} onClick={() => setFiles([])}>
              清空
            </button>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {files.map((file, index) => (
              <div key={index} className="card" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <FileVideo size={20} color="var(--primary)" />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: '500', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {file.name}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                    {(file.size / 1024 / 1024).toFixed(1)} MB
                  </div>
                </div>
                <button className="btn btn-danger" style={{ padding: '6px', borderRadius: '8px' }}
                  onClick={(e) => { e.stopPropagation(); removeFile(index) }}>
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 上传按钮 */}
      <button
        className="btn btn-primary"
        style={{ width: '100%', marginTop: '24px', justifyContent: 'center', padding: '14px', fontSize: '15px', borderRadius: '12px' }}
        onClick={handleUploadAll}
        disabled={files.length === 0 || uploading}
      >
        {uploading ? (
          <><Loader2 size={18} className="animate-spin" /> 上传中...</>
        ) : (
          <><Upload size={18} /> 开始处理 {files.length > 0 && `(${files.length} 个文件)`}</>
        )}
      </button>
    </div>
  )
}

export default UploadPage
