import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileVideo, Loader2, X, Plus, Globe } from 'lucide-react'
import { uploadVideo } from '../api/client'
import { useLang } from '../context/LangContext'

function UploadPage() {
  const [files, setFiles] = useState([])
  const [language, setLanguage] = useState('zh')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()
  const { t } = useLang()

  const addFiles = useCallback((newFiles) => {
    const videoFiles = Array.from(newFiles).filter(f => 
      /\.(mp4|avi|mov|mkv|wmv|flv|webm|m4v)$/i.test(f.name)
    )
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name + f.size))
      return [...prev, ...videoFiles.filter(f => !existing.has(f.name + f.size))]
    })
  }, [])

  const removeFile = (index) => setFiles(prev => prev.filter((_, i) => i !== index))

  const handleUploadAll = async () => {
    if (files.length === 0) return
    setUploading(true)
    
    const results = []
    for (const file of files) {
      try {
        const result = await uploadVideo(file, () => {}, language)
        results.push({ ...result })
      } catch (err) {
        results.push({ error: err.message })
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
    <div style={{ maxWidth: '560px' }}>
      <div className="page-header">
        <h1 className="page-title">{t.uploadTitle}</h1>
        <p className="page-subtitle">{t.uploadSubtitle}</p>
      </div>

      {/* 语言选择 */}
      <div className="card" style={{ marginBottom: '16px', padding: '14px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Globe size={18} color="var(--primary)" />
          <span style={{ fontWeight: '500', fontSize: '14px' }}>{t.outputLang}</span>
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              className={`btn btn-sm ${language === 'zh' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setLanguage('zh')}
            >中文</button>
            <button
              className={`btn btn-sm ${language === 'en' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setLanguage('en')}
            >English</button>
          </div>
        </div>
      </div>

      {/* 拖拽区域 */}
      <div
        className="card"
        style={{
          border: '2px dashed var(--border)',
          textAlign: 'center',
          padding: '48px 32px',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); addFiles(e.dataTransfer.files) }}
      >
        <input ref={fileInputRef} type="file" accept="video/*" multiple
          onChange={(e) => addFiles(e.target.files)} style={{ display: 'none' }} />
        <div style={{
          width: 56, height: 56, borderRadius: 16, background: 'var(--primary-light)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px'
        }}>
          <Plus size={28} color="var(--primary)" />
        </div>
        <p style={{ fontWeight: '500', marginBottom: '4px' }}>{t.dragHere}</p>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{t.multiFiles}</p>
      </div>

      {/* 文件列表 */}
      {files.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              {t.selected} {files.length} {t.files}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={() => setFiles([])}>{t.clear}</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {files.map((file, i) => (
              <div key={i} className="card" style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileVideo size={18} color="var(--primary)" />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {file.name}
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                    {(file.size / 1024 / 1024).toFixed(1)} MB
                  </div>
                </div>
                <button className="btn btn-ghost btn-sm" style={{ padding: '4px' }}
                  onClick={(e) => { e.stopPropagation(); removeFile(i) }}>
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        className="btn btn-primary"
        style={{ width: '100%', marginTop: '20px', justifyContent: 'center', padding: '14px', borderRadius: '12px' }}
        onClick={handleUploadAll}
        disabled={files.length === 0 || uploading}
      >
        {uploading ? <><Loader2 size={18} className="animate-spin" /> {t.uploading}</>
         : <><Upload size={18} /> {t.startProcess} {files.length > 0 && `(${files.length})`}</>}
      </button>
    </div>
  )
}

export default UploadPage
