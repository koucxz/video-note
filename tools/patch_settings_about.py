import pathlib

sp_path = pathlib.Path(r"D:\code\video-note\frontend\src\pages\SettingsPage.jsx")
t = sp_path.read_text(encoding="utf-8")

# Simplify About section - only version
old_about = '''          <div className="card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>{lang === 'zh' ? '关于' : 'About'}</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>{lang === 'zh' ? '版本' : 'Version'}:</span>
                <span style={{ fontWeight: 500 }}>1.1.0</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>{lang === 'zh' ? '框架' : 'Framework'}:</span>
                <span style={{ fontWeight: 500 }}>FastAPI + React</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>{lang === 'zh' ? '数据库' : 'Database'}:</span>
                <span style={{ fontWeight: 500 }}>SQLite</span>
              </div>
            </div>
          </div>'''
new_about = '''          <div className="card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>{lang === 'zh' ? '关于' : 'About'}</h3>
            <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>
              VideoNote v1.2.0
            </div>
          </div>'''
t = t.replace(old_about, new_about, 1)

# Add model config card with edit button
old_model = '''          <div className="card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>{lang === 'zh' ? 'AI 模型配置' : 'AI Model Configuration'}</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>LLM:</span>
                <span style={{ fontWeight: 500 }}>{health?.llm_model || '-'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>VLM:</span>
                <span style={{ fontWeight: 500 }}>{health?.vlm_model || '-'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>ASR:</span>
                <span style={{ fontWeight: 500 }}>{health?.asr_enabled ? (lang === 'zh' ? '已启用' : 'Enabled') : (lang === 'zh' ? '已禁用' : 'Disabled')}</span>
              </div>
            </div>
          </div>'''
new_model = '''          <div className="card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>{lang === 'zh' ? 'AI 模型配置' : 'AI Model Configuration'}</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13, marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>LLM:</span>
                <span style={{ fontWeight: 500 }}>{health?.llm_model || '-'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>VLM:</span>
                <span style={{ fontWeight: 500 }}>{health?.vlm_model || '-'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--gray-400)' }}>ASR:</span>
                <span style={{ fontWeight: 500 }}>{health?.asr_enabled ? (lang === 'zh' ? '已启用' : 'Enabled') : (lang === 'zh' ? '已禁用' : 'Disabled')}</span>
              </div>
            </div>
            <button className="btn btn-outline btn-sm" onClick={() => navigate('/settings/models')}>
              {lang === 'zh' ? '修改配置' : 'Edit Config'}
            </button>
          </div>'''
t = t.replace(old_model, new_model, 1)

sp_path.write_text(t, encoding="utf-8")
print("SettingsPage updated")
