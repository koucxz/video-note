import pathlib

sp = pathlib.Path(r"D:\code\video-note\frontend\src\pages\SettingsPage.jsx")
t = sp.read_text(encoding="utf-8")

old = """      {activeTab === 'models' && (
        <div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>"""
new = """      {activeTab === 'models' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
            <button className="btn btn-primary btn-sm" onClick={saveModelConfig} disabled={saving}>
              {saving ? <Loader2 size={14} className="spin" /> : saved ? <Check size={14} /> : null}
              {saved ? (lang === 'zh' ? '\u5df2\u4fdd\u5b58' : 'Saved') : (lang === 'zh' ? '\u4fdd\u5b58\u914d\u7f6e' : 'Save Config')}
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>"""
t = t.replace(old, new, 1)

sp.write_text(t, encoding="utf-8")
print("done")
