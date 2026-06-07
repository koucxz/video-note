import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, HardDrive, Trash2, CheckSquare, Square, Loader2, AlertTriangle, Activity, Settings, Database, Cpu, Zap, Copy, Check, Eye, EyeOff } from 'lucide-react'
import { useLang } from '../context/LangContext'
import api from '../api/client'

function SettingsPage() {
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const [uploads, setUploads] = useState([])
  const [totalSize, setTotalSize] = useState(0)
  const [uploadDir, setUploadDir] = useState("")
  const [outputDir, setOutputDir] = useState("")
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(new Set())
  const [cleaning, setCleaning] = useState(false)
  const [health, setHealth] = useState(null)
  const [stats, setStats] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [modelConfig, setModelConfig] = useState(null)
  const [showKey, setShowKey] = useState({})
  const [copied, setCopied] = useState({})
  const [editData, setEditData] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      await Promise.all([loadUploads(), loadHealth(), loadStats(), loadModelConfig()])
    } finally {
      setLoading(false)
    }
  }

  const loadUploads = async () => {
    try {
      const resp = await api.get('/storage/uploads')
      setUploads(resp.data.files || [])
      setTotalSize(resp.data.total_size || 0)
      setUploadDir(resp.data.upload_dir || '')
      setOutputDir(resp.data.output_dir || '')
    } catch (err) { console.error(err) }
  }

  const loadHealth = async () => {
    try { setHealth((await api.get('/health')).data) } catch (err) { console.error(err) }
  }

  const loadStats = async () => {
    try {
      const resp = await api.get('/history', { params: { page: 1, size: 1000 } })
      const items = resp.data.items || []
      setStats({
        total: resp.data.total || items.length,
        completed: items.filter(i => i.status === 'completed').length,
        failed: items.filter(i => i.status === 'failed').length,
        processing: items.filter(i => i.status === 'processing').length,
      })
    } catch (err) { console.error(err) }
  }

  const loadModelConfig = async () => {
    try {
      const resp = await api.get('/config/models')
      setModelConfig(resp.data)
      setEditData(resp.data)
    } catch (err) { console.error(err) }
  }

  const saveModelConfig = async () => {
    setSaving(true)
    try {
      const resp = await api.put('/config/models', editData)
      setModelConfig(resp.data)
      setEditData(resp.data)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch { alert(lang === 'zh' ? '保存失败' : 'Save failed') }
    finally { setSaving(false) }
  }

  const updateEdit = (section, field, value) => {
    setEditData(prev => ({
      ...prev,
      [section]: { ...prev[section], [field]: value }
    }))
  }

  const toggleSelect = (hash) => {
    setSelected(s => { const n = new Set(s); n.has(hash) ? n.delete(hash) : n.add(hash); return n })
  }

  const toggleSelectAll = () => {
    if (selected.size === uploads.length) setSelected(new Set())
    else setSelected(new Set(uploads.map(f => f.hash)))
  }

  const cleanSelected = async () => {
    if (!selected.size) return
    if (!confirm(`${t.confirmClean || 'Delete'} ${selected.size}?`)) return
    setCleaning(true)
    try { await api.post('/storage/uploads/clean', [...selected]); setSelected(new Set()); await loadUploads() }
    catch { alert(t.cleanFailed) }
    finally { setCleaning(false) }
  }

  const cleanAll = async () => {
    if (!uploads.length) return
    if (!confirm(`${t.confirmCleanAll || 'Delete ALL'} ${uploads.length} (${formatSize(totalSize)})?`)) return
    setCleaning(true)
    try { await api.post('/storage/uploads/clean', null); setSelected(new Set()); await loadUploads() }
    catch { alert(t.cleanFailed) }
    finally { setCleaning(false) }
  }

  const copyKey = (section, key) => {
    navigator.clipboard.writeText(key)
    setCopied(prev => ({ ...prev, [section]: true }))
    setTimeout(() => setCopied(prev => ({ ...prev, [section]: false })), 1500)
  }

  const maskKey = (key) => {
    if (!key || key.length < 8) return '****'
    return key.slice(0, 4) + '****' + key.slice(-4)
  }

  const formatSize = (bytes) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB'
    return (bytes / 1073741824).toFixed(2) + ' GB'
  }

  const tabs = [
    { id: 'overview', label: lang === 'zh' ? '概览' : 'Overview', icon: Activity },
    { id: 'storage', label: lang === 'zh' ? '存储管理' : 'Storage', icon: HardDrive },
    { id: 'models', label: lang === 'zh' ? '模型配置' : 'Models', icon: Cpu },
    { id: 'about', label: lang === 'zh' ? '关于' : 'About', icon: Settings },
  ]

  const renderModelCard = (title, section) => {
    const cfg = editData?.[section] || modelConfig?.[section]
    if (!cfg) return (
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>{title}</h3>
        <p style={{ color: 'var(--gray-400)', fontSize: 13 }}>{lang === 'zh' ? '加载中...' : 'Loading...'}</p>
      </div>
    )
    const keyVisible = showKey[section]
    return (
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>{title}</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
              {lang === 'zh' ? '模型' : 'Model'}
            </label>
            <input value={cfg.model || ''} onChange={e => updateEdit(section, 'model', e.target.value)}
              style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'inherit', outline: 'none' }} />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
              {lang === 'zh' ? 'API 地址' : 'Base URL'}
            </label>
            <input value={cfg.base_url || ''} onChange={e => updateEdit(section, 'base_url', e.target.value)}
              style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'inherit', outline: 'none' }} />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
              API Key {cfg.api_key_set && <span style={{ color: 'var(--green)', fontWeight: 400 }}>({lang === 'zh' ? '已设置' : 'set'})</span>}
            </label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                type={keyVisible ? 'text' : 'password'}
                value={cfg.api_key || ''}
                placeholder={cfg.api_key_set ? (lang === 'zh' ? '留空保持不变' : 'Keep current') : 'sk-...'}
                onChange={e => updateEdit(section, 'api_key', e.target.value)}
                style={{ flex: 1, padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'monospace', outline: 'none' }} />
              <button onClick={() => setShowKey(p => ({ ...p, [section]: !p[section] }))}
                style={{ background: 'none', border: '1px solid var(--gray-200)', borderRadius: 8, cursor: 'pointer', padding: '8px', display: 'flex', color: 'var(--gray-400)' }}>
                {keyVisible ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
              {cfg.api_key && (
                <button onClick={() => copyKey(section, cfg.api_key)}
                  style={{ background: 'none', border: '1px solid var(--gray-200)', borderRadius: 8, cursor: 'pointer', padding: '8px', display: 'flex', color: 'var(--gray-400)' }}>
                  {copied[section] ? <Check size={14} color="var(--green)" /> : <Copy size={14} />}
                </button>
              )}
            </div>
          </div>
          {section === 'asr' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <input type="checkbox" checked={cfg.enabled || false}
                onChange={e => updateEdit('asr', 'enabled', e.target.checked)}
                style={{ width: 16, height: 16, cursor: 'pointer' }} />
              <span style={{ fontSize: 14 }}>{lang === 'zh' ? '启用语音识别' : 'Enable ASR'}</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <Loader2 size={36} className="spin" color="var(--blue)" />
    </div>
  )

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')} style={{ padding: '4px 8px' }}>
          <ArrowLeft size={16} />
        </button>
        <Settings size={24} color="var(--blue)" />
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>{t.settings || 'Settings'}</h1>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--gray-200)', paddingBottom: 4 }}>
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 16px', borderRadius: '8px 8px 0 0',
                border: 'none', background: activeTab === tab.id ? 'var(--blue-light)' : 'transparent',
                color: activeTab === tab.id ? 'var(--blue)' : 'var(--gray-500)',
                fontWeight: activeTab === tab.id ? 600 : 400,
                cursor: 'pointer', fontSize: 14, fontFamily: 'inherit',
              }}>
              <Icon size={16} />{tab.label}
            </button>
          )
        })}
      </div>

      {/* Overview */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <Database size={18} color="var(--blue)" />
              <h3 style={{ fontSize: 14, fontWeight: 600 }}>{lang === 'zh' ? '任务统计' : 'Task Statistics'}</h3>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div><div style={{ fontSize: 24, fontWeight: 700, color: 'var(--blue)' }}>{stats?.total || 0}</div><div style={{ fontSize: 12, color: 'var(--gray-400)' }}>{lang === 'zh' ? '总任务' : 'Total'}</div></div>
              <div><div style={{ fontSize: 24, fontWeight: 700, color: 'var(--green)' }}>{stats?.completed || 0}</div><div style={{ fontSize: 12, color: 'var(--gray-400)' }}>{lang === 'zh' ? '已完成' : 'Completed'}</div></div>
              <div><div style={{ fontSize: 24, fontWeight: 700, color: 'var(--red)' }}>{stats?.failed || 0}</div><div style={{ fontSize: 12, color: 'var(--gray-400)' }}>{lang === 'zh' ? '失败' : 'Failed'}</div></div>
              <div><div style={{ fontSize: 24, fontWeight: 700, color: 'var(--blue)' }}>{stats?.processing || 0}</div><div style={{ fontSize: 12, color: 'var(--gray-400)' }}>{lang === 'zh' ? '处理中' : 'Processing'}</div></div>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <HardDrive size={18} color="var(--green)" />
              <h3 style={{ fontSize: 14, fontWeight: 600 }}>{lang === 'zh' ? '存储使用' : 'Storage Usage'}</h3>
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--green)', marginBottom: 4 }}>{formatSize(totalSize)}</div>
            <div style={{ fontSize: 13, color: 'var(--gray-400)' }}>{uploads.length} {lang === 'zh' ? '个视频文件' : 'video files'}</div>
            <button className="btn btn-ghost btn-sm" style={{ marginTop: 12 }} onClick={() => setActiveTab('storage')}>
              {lang === 'zh' ? '管理存储 →' : 'Manage Storage →'}
            </button>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <Zap size={18} color="var(--orange, #f59e0b)" />
              <h3 style={{ fontSize: 14, fontWeight: 600 }}>{lang === 'zh' ? '服务状态' : 'Service Status'}</h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: health ? 'var(--green)' : 'var(--red)' }} />
              <span style={{ fontSize: 14 }}>{health ? (lang === 'zh' ? '服务正常' : 'Healthy') : (lang === 'zh' ? '服务异常' : 'Unhealthy')}</span>
            </div>
            {health && (
              <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>
                <div>LLM: {health.llm_model}</div>
                <div>VLM: {health.vlm_model}</div>
                <div>ASR: {health.asr_enabled ? (lang === 'zh' ? '已启用' : 'Enabled') : (lang === 'zh' ? '已禁用' : 'Disabled')}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Storage */}
      {activeTab === 'storage' && (
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <HardDrive size={20} color="var(--blue)" />
              <h2 style={{ fontSize: 16, fontWeight: 700 }}>{lang === 'zh' ? '上传视频管理' : 'Uploaded Videos'}</h2>
            </div>
            <div style={{ display: 'flex', gap: 20, marginBottom: 12, fontSize: 14 }}>
              <span>{lang === 'zh' ? '文件数' : 'Files'}: <strong>{uploads.length}</strong></span>
              <span>{lang === 'zh' ? '总大小' : 'Total'}: <strong>{formatSize(totalSize)}</strong></span>
            </div>

            {uploads.length > 0 && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                <button className="btn btn-ghost btn-sm" onClick={toggleSelectAll}>
                  {selected.size === uploads.length ? <CheckSquare size={14} /> : <Square size={14} />}
                  {selected.size > 0 ? `${t.selected || 'Selected'} ${selected.size}` : (t.selectAll || 'Select All')}
                </button>
                <button className="btn btn-outline btn-sm" onClick={cleanSelected} disabled={!selected.size || cleaning}>
                  {cleaning ? <Loader2 size={14} className="spin" /> : <Trash2 size={14} />}
                  {t.cleanSelected} {selected.size > 0 && `(${selected.size})`}
                </button>
                <button className="btn btn-primary btn-sm" style={{ background: 'var(--red)' }} onClick={cleanAll} disabled={!uploads.length || cleaning}>
                  {cleaning ? <Loader2 size={14} className="spin" /> : <AlertTriangle size={14} />}
                  {t.cleanAll} ({formatSize(totalSize)})
                </button>
              </div>
            )}
          </div>
          {uploads.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
              <HardDrive size={32} color="var(--gray-300)" style={{ margin: '0 auto 8px' }} />
              <p style={{ color: 'var(--gray-400)', fontSize: 14 }}>{t.noUploads}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {uploads.map((file) => {
                const isSelected = selected.has(file.hash)
                return (
                  <div key={file.hash} className="hist-row" style={{ padding: '10px 14px', background: isSelected ? 'var(--blue-light)' : undefined, display: 'flex', alignItems: 'center', gap: 10 }}>
                    <button onClick={() => toggleSelect(file.hash)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, display: 'flex' }}>
                      {isSelected ? <CheckSquare size={16} color="var(--blue)" /> : <Square size={16} color="var(--gray-300)" />}
                    </button>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.filename}</div>
                      <div style={{ fontSize: 10, color: 'var(--gray-400)', fontFamily: 'monospace', wordBreak: 'break-all' }}>{file.path}</div>
                    </div>
                    <span style={{ fontSize: 13, color: 'var(--gray-500)', flexShrink: 0 }}>{formatSize(file.size)}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Models */}
      {activeTab === 'models' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700 }}>{lang === 'zh' ? '模型配置' : 'Model Configuration'}</h2>
            <button className="btn btn-primary btn-sm" onClick={saveModelConfig} disabled={saving}>
              {saving ? <Loader2 size={14} className="spin" /> : saved ? <Check size={14} /> : null}
              {saved ? (lang === 'zh' ? '已保存' : 'Saved') : (lang === 'zh' ? '保存配置' : 'Save')}
            </button>
          </div>
          {['llm', 'vlm', 'asr'].map((section, idx) => {
            const titles = { llm: lang === 'zh' ? '文本模型 (LLM)' : 'Language Model (LLM)',
                             vlm: lang === 'zh' ? '视觉模型 (VLM)' : 'Vision Model (VLM)',
                             asr: lang === 'zh' ? '语音识别 (ASR)' : 'Speech Recognition (ASR)' }
            const cfg = editData?.[section] || {}
            const keyVisible = showKey[section]
            return (
              <div key={section} style={{ marginBottom: idx < 2 ? 24 : 0, paddingBottom: idx < 2 ? 24 : 0, borderBottom: idx < 2 ? '1px solid var(--gray-200)' : 'none' }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 14 }}>{titles[section]}</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
                  {section !== 'asr' && (
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
                      {lang === 'zh' ? '协议' : 'Protocol'}
                    </label>
                    <select value={cfg.type || 'openai'} onChange={e => updateEdit(section, 'type', e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'inherit', outline: 'none', background: 'white', boxSizing: 'border-box' }}>
                      <option value="openai">OpenAI Compatible</option>
                      <option value="anthropic">Anthropic (Claude)</option>
                    </select>
                  </div>
                  )}
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
                      {lang === 'zh' ? '模型' : 'Model'}
                    </label>
                    <input value={cfg.model || ''} onChange={e => updateEdit(section, 'model', e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
                      {lang === 'zh' ? 'API 地址' : 'Base URL'}
                    </label>
                    <input value={cfg.base_url || ''} onChange={e => updateEdit(section, 'base_url', e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
                      API Key {cfg.api_key_set ? <span style={{ color: 'var(--green)', fontWeight: 400 }}>({lang === 'zh' ? '已设置' : 'set'})</span> : null}
                    </label>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <input
                        type={keyVisible ? 'text' : 'password'}
                        value={cfg.api_key || ''}
                        placeholder={cfg.api_key_set ? (lang === 'zh' ? '留空保持不变' : 'Keep current') : 'sk-...'}
                        onChange={e => updateEdit(section, 'api_key', e.target.value)}
                        style={{ flex: 1, padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'monospace', outline: 'none', boxSizing: 'border-box' }} />
                      <button onClick={() => setShowKey(p => ({ ...p, [section]: !p[section] }))}
                        style={{ background: 'none', border: '1px solid var(--gray-200)', borderRadius: 8, cursor: 'pointer', padding: '8px', display: 'flex', color: 'var(--gray-400)' }}>
                        {keyVisible ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                      {cfg.api_key ? (
                        <button onClick={() => copyKey(section, cfg.api_key)}
                          style={{ background: 'none', border: '1px solid var(--gray-200)', borderRadius: 8, cursor: 'pointer', padding: '8px', display: 'flex', color: 'var(--gray-400)' }}>
                          {copied[section] ? <Check size={14} color="var(--green)" /> : <Copy size={14} />}
                        </button>
                      ) : null}
                    </div>
                  </div>
                  {section === 'asr' && (
                    <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 4 }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                        <input type="checkbox" checked={cfg.enabled || false}
                          onChange={e => updateEdit('asr', 'enabled', e.target.checked)}
                          style={{ width: 16, height: 16, cursor: 'pointer' }} />
                        <span style={{ fontSize: 13 }}>{lang === 'zh' ? '启用语音识别' : 'Enable ASR'}</span>
                      </label>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* About */}
      {activeTab === 'about' && (
        <div className="card">
          <div style={{ fontSize: 14, color: 'var(--gray-500)', lineHeight: 2, textAlign: 'center' }}>
            VideoNote v1.2.0
          </div>
        </div>
      )}
    </div>
  )
}

export default SettingsPage
