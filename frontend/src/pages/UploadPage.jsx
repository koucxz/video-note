import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileVideo, Loader2, X, Plus, Globe, Check } from 'lucide-react'
import { uploadVideo } from '../api/client'
import { useLang } from '../context/LangContext'

function UploadPage() {
  const [files, setFiles] = useState([])
  const [language, setLanguage] = useState('zh')
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
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
    <div style={{ maxWidth: '580px' }}>
      <div className="page-header">
        <h1 className="page-title">{t.uploadTitle}</h1>
        <p className="page-subtitle">{t.uploadSubtitle}</p>
      </div>

      {/* 语言选择 - 更紧凑的标签式 */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <Globe size={14} color="var(--text-muted)" />
          <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            {t.outputLang}
          </span>
        </div>
        <div className="tag-group">
          <button className={`tag-btn ${language === 'zh' ? 'active' : ''}`} onClick={() => setLanguage('zh')}>
            {language === 'zh' && <Check size={12} style={{ marginRight: 4 }} />}
            中文
          </button>
          <button className={`tag-btn ${language === 'en' ? 'active' : ''}`} onClick={() => setLanguage('en')}>
            {language === 'en' && <Check size={12} style={{ marginRight: 4 }} />}
            English
          </button>
        </div>
      </div>

      {/* 上传区域 */}
      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files) }}
      >
        <input ref={fileInputRef} type="file" accept="video/*" multiple
          onChange={(e) => addFiles(e.target.files)} style={{ display: 'none' }} />
        
        <div style={{
          width: 52, height: 52, borderRadius: '50%', background: 'var(--primary-light)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px'
        }}>
          <Plus size={24} color="var(--primary)" />
        </div>
        <p style={{ fontWeight: '600', fontSize: '15px', marginBottom: '4px' }}>{t.dragHere}</p>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{t.multiFiles}</p>
      </div>

      {/* 文件列表 */}
      {files.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              {t.selected} {files.length} {t.files}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={() => setFiles([])}>{t.clear}</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {files.map((file, i) => (
              <div key={i} className="file-item animate-in">
                <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-sm)', background: 'var(--primary-light)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FileVideo size={18} color="var(--primary)" />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '14px', fontWeight: '500', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {file.name}
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '1px' }}>
                    {(file.size / 1024 / 1024).toFixed(1)} MB
                  </div>
                </div>
                <button className="btn btn-ghost btn-sm" style={{ padding: '6px', borderRadius: 'var(--radius-sm)' }}
                  onClick={(e) => { e.stopPropagation(); removeFile(i) }}>
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 上传按钮 */}
      <button
        className="btn btn-primary btn-lg btn-block"
        style={{ marginTop: '24px' }}
        onClick={handleUploadAll}
        disabled={files.length === 0 || uploading}
      >
        {uploading ? (
          <><Loader2 size={18} className="animate-spin" /> {t.uploading}</>
        ) : (
          <><Upload size={18} /> {t.startProcess} {files.length > 0 && `(${files.length})`}</>
        )}
      </button>
    </div>
  )
}

export default UploadPage
