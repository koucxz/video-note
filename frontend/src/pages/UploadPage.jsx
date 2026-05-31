import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileVideo, Loader2 } from 'lucide-react'
import { uploadVideo } from '../api/client'

function UploadPage() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()

  const handleFileSelect = (e) => {
    const selected = e.target.files[0]
    if (selected) {
      setFile(selected)
      setError(null)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files[0]
    if (dropped) {
      setFile(dropped)
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    
    setUploading(true)
    setError(null)
    
    try {
      const result = await uploadVideo(file, setProgress)
      navigate(`/processing/${result.task_id}`)
    } catch (err) {
      setError(err.message || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '8px' }}>
        上传视频
      </h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>
        支持 MP4, AVI, MOV, MKV 等格式
      </p>

      <div
        className="card"
        style={{
          border: '2px dashed var(--border)',
          textAlign: 'center',
          padding: '48px',
          cursor: 'pointer',
          transition: 'border-color 0.2s'
        }}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        
        {file ? (
          <div>
            <FileVideo size={48} color="var(--primary)" />
            <p style={{ marginTop: '16px', fontWeight: '500' }}>{file.name}</p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        ) : (
          <div>
            <Upload size={48} color="var(--text-secondary)" />
            <p style={{ marginTop: '16px' }}>
              点击或拖拽视频文件到此处
            </p>
          </div>
        )}
      </div>

      {error && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: '#fef2f2',
          borderRadius: '8px',
          color: 'var(--error)'
        }}>
          {error}
        </div>
      )}

      {uploading && (
        <div style={{ marginTop: '16px' }}>
          <div style={{
            height: '8px',
            background: 'var(--border)',
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div style={{
              height: '100%',
              background: 'var(--primary)',
              width: `${progress}%`,
              transition: 'width 0.3s'
            }} />
          </div>
          <p style={{ marginTop: '8px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            上传中... {progress}%
          </p>
        </div>
      )}

      <button
        className="btn btn-primary"
        style={{ width: '100%', marginTop: '24px', justifyContent: 'center' }}
        onClick={handleUpload}
        disabled={!file || uploading}
      >
        {uploading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            上传中...
          </>
        ) : (
          <>
            <Upload size={16} />
            开始处理
          </>
        )}
      </button>
    </div>
  )
}

export default UploadPage
