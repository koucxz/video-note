import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Cpu, Save, Loader2, Check, Eye, EyeOff } from 'lucide-react'
import { useLang } from '../context/LangContext'
import api from '../api/client'

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI Compatible' },
]

const PRESET_MODELS = {
  llm: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'claude-3-5-sonnet-20241022'],
  vlm: ['gpt-4o', 'gpt-4o-mini', 'claude-3-5-sonnet-20241022'],
  asr: ['whisper-1'],
}

function ModelConfigPage() {
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [showKeys, setShowKeys] = useState({})

  useEffect(() => { loadConfig() }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const resp = await api.get('/config/models')
      setConfig(resp.data)
    } catch (err) {
      console.error('Failed to load config:', err)
    } finally {
      setLoading(false)
    }
  }

  const updateField = (section, field, value) => {
    setConfig(prev => ({
      ...prev,
      [section]: { ...prev[section], [field]: value }
    }))
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      await api.put('/config/models', config)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      alert(lang === 'zh' ? '保存失败' : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const toggleShowKey = (section) => {
    setShowKeys(prev => ({ ...prev, [section]: !prev[section] }))
  }

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '120px 0' }}>
      <Loader2 size={36} className="spin" color="var(--blue)" />
    </div>
  )

  const renderSection = (title, section, key) => (
    <div className="card" style={{ marginBottom: 16 }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Cpu size={16} color="var(--blue)" />
        {title}
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Model */}
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
            {lang === 'zh' ? '模型' : 'Model'}
          </label>
          <input
            list={`models-${key}`}
            value={config?.[key]?.model || ''}
            onChange={e => updateField(key, 'model', e.target.value)}
            style={{
              width: '100%', padding: '8px 12px', borderRadius: 8,
              border: '1.5px solid var(--gray-200)', fontSize: 14,
              fontFamily: 'inherit', outline: 'none',
            }}
          />
          <datalist id={`models-${key}`}>
            {(PRESET_MODELS[key] || []).map(m => <option key={m} value={m} />)}
          </datalist>
        </div>

        {/* Base URL */}
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
            {lang === 'zh' ? 'API 地址' : 'Base URL'}
          </label>
          <input
            value={config?.[key]?.base_url || ''}
            onChange={e => updateField(key, 'base_url', e.target.value)}
            style={{
              width: '100%', padding: '8px 12px', borderRadius: 8,
              border: '1.5px solid var(--gray-200)', fontSize: 14,
              fontFamily: 'inherit', outline: 'none',
            }}
          />
        </div>

        {/* API Key */}
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
            API Key {config?.[key]?.api_key_set && <span style={{ color: 'var(--green)' }}>({lang === 'zh' ? '已设置' : 'set'})</span>}
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type={showKeys[key] ? 'text' : 'password'}
              placeholder={config?.[key]?.api_key_set ? (lang === 'zh' ? '留空则保持不变' : 'Leave empty to keep') : 'sk-...'}
              onChange={e => updateField(key, 'api_key', e.target.value)}
              style={{
                flex: 1, padding: '8px 12px', borderRadius: 8,
                border: '1.5px solid var(--gray-200)', fontSize: 14,
                fontFamily: 'inherit', outline: 'none',
              }}
            />
            <button className="btn btn-ghost btn-sm" onClick={() => toggleShowKey(key)} style={{ padding: '8px' }}>
              {showKeys[key] ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        {/* ASR toggle */}
        {key === 'asr' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input
              type="checkbox"
              checked={config?.asr?.enabled || false}
              onChange={e => updateField('asr', 'enabled', e.target.checked)}
              style={{ width: 16, height: 16, cursor: 'pointer' }}
            />
            <span style={{ fontSize: 14 }}>{lang === 'zh' ? '启用语音识别 (ASR)' : 'Enable Speech Recognition (ASR)'}</span>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div style={{ maxWidth: 640, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/settings')} style={{ padding: '4px 8px' }}>
            <ArrowLeft size={16} />
          </button>
          <h1 style={{ fontSize: 20, fontWeight: 800 }}>{lang === 'zh' ? '模型配置' : 'Model Configuration'}</h1>
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 size={16} className="spin" /> : saved ? <Check size={16} /> : <Save size={16} />}
          {saved ? (lang === 'zh' ? '已保存' : 'Saved') : (lang === 'zh' ? '保存' : 'Save')}
        </button>
      </div>

      {renderSection(lang === 'zh' ? '文本模型 (LLM)' : 'Language Model (LLM)', 'llm', 'llm')}
      {renderSection(lang === 'zh' ? '视觉模型 (VLM)' : 'Vision Model (VLM)', 'vlm', 'vlm')}
      {renderSection(lang === 'zh' ? '语音识别 (ASR)' : 'Speech Recognition (ASR)', 'asr', 'asr')}
    </div>
  )
}

export default ModelConfigPage
