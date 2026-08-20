import pathlib

hp = pathlib.Path(r"D:\code\video-note\frontend\src\pages\HistoryPage.jsx")
t = hp.read_text(encoding="utf-8")

# Fix the broken merge - add missing lines between batch bar and card list
old = """        </div>
                <span className={`badge ${s.badge}`}>{s.label}</span>"""

new = """        </div>
      )}

      {filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '56px 24px' }}>
          <div className="dropzone-icon" style={{ margin: '0 auto 14px' }}>
            <History size={28} color="var(--blue)" />
          </div>
          <p style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>{search ? '\u672a\u627e\u5230\u5339\u914d\u8bb0\u5f55' : t.noRecords}</p>
          {!search && <p style={{ color: 'var(--gray-400)', fontSize: 13, marginBottom: 20 }}>{t.uploadFirst}</p>}
          <button className="btn btn-primary" onClick={() => navigate('/')}>{t.upload}</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 10 }}>
          {filtered.map((item) => {
            const s = statusMap[item.status] || statusMap.pending
            const Icon = s.icon
            const canView = item.status === 'completed'
            const isSelected = selected.has(item.task_id)
            return (
              <div key={item.task_id} className="hist-row in"
                onClick={() => canView && navigate(`/note/${item.task_id}`)}
                style={{ padding: '12px 14px', background: isSelected ? 'var(--blue-light)' : undefined }}>
                <div className="checkbox-col" style={{ display: 'flex', alignItems: 'center' }}>
                  {canView && (
                    <button onClick={(e) => { e.stopPropagation(); toggleSelect(item.task_id) }}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, display: 'flex' }}>
                      {isSelected ? <CheckSquare size={16} color="var(--blue)" /> : <Square size={16} color="var(--gray-300)" />}
                    </button>
                  )}
                </div>
                <div className="hist-icon" style={{ background: s.bg, width: 36, height: 36, borderRadius: 8 }}>
                  <Icon size={16} color={s.color} className={item.status === 'processing' ? 'spin' : ''} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.videoName}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 1 }}>{formatDate(item.createdAt)}</div>
                </div>
                <span className={`badge ${s.badge}`}>{s.label}</span>"""

if old in t:
    t = t.replace(old, new, 1)
    print("fixed")
else:
    print("pattern not found")
    # Show what's around line 191
    lines = t.split('\n')
    for i in range(188, 196):
        print(f'{i+1}: {repr(lines[i])}')

hp.write_text(t, encoding="utf-8")
