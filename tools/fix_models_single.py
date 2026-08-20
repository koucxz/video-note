import pathlib

sp = pathlib.Path(r"D:\code\video-note\frontend\src\pages\SettingsPage.jsx")
t = sp.read_text(encoding="utf-8")

# Replace the models tab content with a single card
old = """      {activeTab === 'models' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
            <button className="btn btn-primary btn-sm" onClick={saveModelConfig} disabled={saving}>
              {saving ? <Loader2 size={14} className="spin" /> : saved ? <Check size={14} /> : null}
              {saved ? (lang === 'zh' ? '\u5df2\u4fdd\u5b58' : 'Saved') : (lang === 'zh' ? '\u4fdd\u5b58\u914d\u7f6e' : 'Save Config')}
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
            {renderModelCard(lang === 'zh' ? '\u6587\u672c\u6a21\u578b (LLM)' : 'Language Model (LLM)', 'llm')}
            {renderModelCard(lang === 'zh' ? '\u89c6\u89c9\u6a21\u578b (VLM)' : 'Vision Model (VLM)', 'vlm')}
            {renderModelCard(lang === 'zh' ? '\u8bed\u97f3\u8bc6\u522b (ASR)' : 'Speech Recognition (ASR)', 'asr')}
          </div>
        </div>
      )}"""

new = """      {activeTab === 'models' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700 }}>{lang === 'zh' ? '\u6a21\u578b\u914d\u7f6e' : 'Model Configuration'}</h2>
            <button className="btn btn-primary btn-sm" onClick={saveModelConfig} disabled={saving}>
              {saving ? <Loader2 size={14} className="spin" /> : saved ? <Check size={14} /> : null}
              {saved ? (lang === 'zh' ? '\u5df2\u4fdd\u5b58' : 'Saved') : (lang === 'zh' ? '\u4fdd\u5b58\u914d\u7f6e' : 'Save')}
            </button>
          </div>
          {['llm', 'vlm', 'asr'].map((section, idx) => {
            const titles = { llm: lang === 'zh' ? '\u6587\u672c\u6a21\u578b (LLM)' : 'Language Model (LLM)',
                             vlm: lang === 'zh' ? '\u89c6\u89c9\u6a21\u578b (VLM)' : 'Vision Model (VLM)',
                             asr: lang === 'zh' ? '\u8bed\u97f3\u8bc6\u522b (ASR)' : 'Speech Recognition (ASR)' }
            const cfg = editData?.[section] || {}
            const keyVisible = showKey[section]
            return (
              <div key={section} style={{ marginBottom: idx < 2 ? 24 : 0, paddingBottom: idx < 2 ? 24 : 0, borderBottom: idx < 2 ? '1px solid var(--gray-200)' : 'none' }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 14 }}>{titles[section]}</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
                      {lang === 'zh' ? '\u6a21\u578b' : 'Model'}
                    </label>
                    <input value={cfg.model || ''} onChange={e => updateEdit(section, 'model', e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
                      {lang === 'zh' ? 'API \u5730\u5740' : 'Base URL'}
                    </label>
                    <input value={cfg.base_url || ''} onChange={e => updateEdit(section, 'base_url', e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid var(--gray-200)', fontSize: 13, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 4, display: 'block' }}>
                      API Key {cfg.api_key_set ? <span style={{ color: 'var(--green)', fontWeight: 400 }}>({lang === 'zh' ? '\u5df2\u8bbe\u7f6e' : 'set'})</span> : null}
                    </label>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <input
                        type={keyVisible ? 'text' : 'password'}
                        value={cfg.api_key || ''}
                        placeholder={cfg.api_key_set ? (lang === 'zh' ? '\u7559\u7a7a\u4fdd\u6301\u4e0d\u53d8' : 'Keep current') : 'sk-...'}
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
                        <span style={{ fontSize: 13 }}>{lang === 'zh' ? '\u542f\u7528\u8bed\u97f3\u8bc6\u522b' : 'Enable ASR'}</span>
                      </label>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}"""

if old in t:
    t = t.replace(old, new, 1)
    print("replaced models tab")
else:
    print("old not found, trying line-based")
    lines = t.split('\n')
    start = None
    end = None
    for i, line in enumerate(lines):
        if "activeTab === 'models'" in line:
            start = i
        if start and i > start and line.strip() == ')}' and i > start + 5:
            end = i
            break
    if start and end:
        new_lines = lines[:start]
        new_lines.extend(new.strip().split('\n'))
        new_lines.extend(lines[end+1:])
        t = '\n'.join(new_lines)
        print("replaced via line splice")

sp.write_text(t, encoding="utf-8")
print("done")
