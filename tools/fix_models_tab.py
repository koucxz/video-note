import pathlib

sp = pathlib.Path(r"D:\code\video-note\frontend\src\pages\SettingsPage.jsx")
t = sp.read_text(encoding="utf-8")

# 1. Remove the "Edit Config" button and navigate import for models
old_nav = """          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/settings/models')}>
              {lang === 'zh' ? '编辑配置' : 'Edit Config'}
            </button>
          </div>"""
if old_nav in t:
    t = t.replace(old_nav, "", 1)
    print("removed edit config button")

# 2. Replace the models tab content with inline editable version
old_models = """      {/* Models */}
      {activeTab === 'models' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/settings/models')}>
              {lang === 'zh' ? '编辑配置' : 'Edit Config'}
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
            {renderModelCard(lang === 'zh' ? '文本模型 (LLM)' : 'Language Model (LLM)', 'llm')}
            {renderModelCard(lang === 'zh' ? '视觉模型 (VLM)' : 'Vision Model (VLM)', 'vlm')}
            {renderModelCard(lang === 'zh' ? '语音识别 (ASR)' : 'Speech Recognition (ASR)', 'asr')}
          </div>
        </div>
      )}"""

new_models = """      {/* Models */}
      {activeTab === 'models' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
          {renderModelCard(lang === 'zh' ? '文本模型 (LLM)' : 'Language Model (LLM)', 'llm')}
          {renderModelCard(lang === 'zh' ? '视觉模型 (VLM)' : 'Vision Model (VLM)', 'vlm')}
          {renderModelCard(lang === 'zh' ? '语音识别 (ASR)' : 'Speech Recognition (ASR)', 'asr')}
        </div>
      )}"""
t = t.replace(old_models, new_models, 1)

# 3. Add editing state and saving logic
old_state = "  const [copied, setCopied] = useState({})"
new_state = """  const [copied, setCopied] = useState({})
  const [editData, setEditData] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)"""
t = t.replace(old_state, new_state, 1)

# 4. Initialize editData when modelConfig loads
old_load = "  const loadModelConfig = async () => {\n    try { setModelConfig((await api.get('/config/models')).data) } catch (err) { console.error(err) }"
new_load = """  const loadModelConfig = async () => {
    try {
      const resp = await api.get('/config/models')
      setModelConfig(resp.data)
      setEditData(resp.data)
    } catch (err) { console.error(err) }"""
t = t.replace(old_load, new_load, 1)

# 5. Add save function after loadModelConfig
old_after_load = "  const toggleSelect = (hash) => {"
new_after_load = """  const saveModelConfig = async () => {
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

  const toggleSelect = (hash) => {"""
t = t.replace(old_after_load, new_after_load, 1)

# 6. Rewrite renderModelCard to be editable with proper display
old_render = """  const renderModelCard = (title, section) => {
    const cfg = modelConfig?.[section]
    if (!cfg) return null
    const keyVisible = showKey[section]
    return (
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>{title}</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>{lang === 'zh' ? '模型' : 'Model'}</span>
            <span style={{ fontSize: 13, fontWeight: 600 }}>{cfg.model || '-'}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>{lang === 'zh' ? 'API 地址' : 'Base URL'}</span>
            <span style={{ fontSize: 13, fontWeight: 500, maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{cfg.base_url || '-'}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>API Key</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 13, fontFamily: 'monospace', letterSpacing: 1 }}>
                {cfg.api_key_set ? (keyVisible ? cfg.api_key : maskKey(cfg.api_key)) : (lang === 'zh' ? '未设置' : 'Not set')}
              </span>
              {cfg.api_key_set && (
                <>
                  <button onClick={() => setShowKey(p => ({ ...p, [section]: !p[section] }))}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, display: 'flex', color: 'var(--gray-400)' }}>
                    {keyVisible ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                  <button onClick={() => copyKey(section, cfg.api_key)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, display: 'flex', color: 'var(--gray-400)' }}>
                    {copied[section] ? <Check size={14} color="var(--green)" /> : <Copy size={14} />}
                  </button>
                </>
              )}
            </div>
          </div>
          {section === 'asr' && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>{lang === 'zh' ? '状态' : 'Status'}</span>
              <span style={{ fontSize: 13, fontWeight: 500, color: cfg.enabled ? 'var(--green)' : 'var(--gray-400)' }}>
                {cfg.enabled ? (lang === 'zh' ? '已启用' : 'Enabled') : (lang === 'zh' ? '已禁用' : 'Disabled')}
              </span>
            </div>
          )}
        </div>
      </div>
    )
  }"""

new_render = """  const renderModelCard = (title, section) => {
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
  }"""
t = t.replace(old_render, new_render, 1)

# 7. Add save button in models tab header
old_models_div = """      {/* Models */}
      {activeTab === 'models' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
          {renderModelCard(lang === 'zh' ? '文本模型 (LLM)' : 'Language Model (LLM)', 'llm')}
          {renderModelCard(lang === 'zh' ? '视觉模型 (VLM)' : 'Vision Model (VLM)', 'vlm')}
          {renderModelCard(lang === 'zh' ? '语音识别 (ASR)' : 'Speech Recognition (ASR)', 'asr')}
        </div>
      )}"""
new_models_div = """      {/* Models */}
      {activeTab === 'models' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
            <button className="btn btn-primary btn-sm" onClick={saveModelConfig} disabled={saving}>
              {saving ? <Loader2 size={14} className="spin" /> : saved ? <Check size={14} /> : null}
              {saved ? (lang === 'zh' ? '已保存' : 'Saved') : (lang === 'zh' ? '保存配置' : 'Save Config')}
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
            {renderModelCard(lang === 'zh' ? '文本模型 (LLM)' : 'Language Model (LLM)', 'llm')}
            {renderModelCard(lang === 'zh' ? '视觉模型 (VLM)' : 'Vision Model (VLM)', 'vlm')}
            {renderModelCard(lang === 'zh' ? '语音识别 (ASR)' : 'Speech Recognition (ASR)', 'asr')}
          </div>
        </div>
      )}"""
t = t.replace(old_models_div, new_models_div, 1)

sp.write_text(t, encoding="utf-8")
print("done")
