import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Folder, Plus, Pencil, Trash2, ArrowLeft, FolderOpen } from 'lucide-react'
import { useCollections } from '../hooks/useCollections'
import { getHistoryAll } from '../api/client'
import { useLang } from '../context/LangContext'

const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ec4899', '#3b82f6', '#8b5cf6', '#ef4444', '#14b8a6']

function colorFor(id) {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return COLORS[h % COLORS.length]
}

export default function CollectionsPage() {
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const { collections, addCollection, removeCollection, addToCollection, removeFromCollection } = useCollections()
  const [notes, setNotes] = useState([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [selectedCol, setSelectedCol] = useState(null)

  useEffect(() => { getHistoryAll().then(list => setNotes(list.filter(i => i.status === 'completed'))) }, [])

  const handleCreate = () => {
    if (!newName.trim()) return
    addCollection(newName.trim())
    setNewName('')
    setDialogOpen(false)
  }

  const completedNotes = notes.filter(n => {
    const inAny = collections.some(c => c.noteIds.includes(n.task_id))
    return selectedCol ? true : !inAny
  })

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')}><ArrowLeft size={16} /></button>
        <h1 style={{ fontSize: 20, fontWeight: 800 }}>{lang === 'zh' ? '分类合集' : 'Collections'}</h1>
      </div>

      {/* Collection cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
        {collections.map(col => (
          <div key={col.id} onClick={() => setSelectedCol(selectedCol === col.id ? null : col.id)}
            style={{
              padding: 20, borderRadius: 12, cursor: 'pointer', border: selectedCol === col.id ? '2px solid var(--blue)' : '1px solid var(--gray-200)',
              background: selectedCol === col.id ? 'var(--blue-light)' : 'white', transition: 'all 0.15s',
            }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: colorFor(col.id) + '20', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
              <Folder size={20} color={colorFor(col.id)} />
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{col.name}</div>
            <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>{col.noteIds.length} {lang === 'zh' ? '篇笔记' : 'notes'}</div>
            <button onClick={(e) => { e.stopPropagation(); if (confirm(lang === 'zh' ? '删除此合集？' : 'Delete collection?')) removeCollection(col.id) }}
              style={{ position: 'absolute', top: 8, right: 8, background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
              <Trash2 size={14} color="var(--gray-400)" />
            </button>
          </div>
        ))}
        {/* Add new */}
        <div onClick={() => setDialogOpen(true)}
          style={{ padding: 20, borderRadius: 12, border: '2px dashed var(--gray-200)', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, minHeight: 120 }}>
          <Plus size={24} color="var(--gray-400)" />
          <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>{lang === 'zh' ? '新建合集' : 'New Collection'}</span>
        </div>
      </div>

      {/* Create dialog */}
      {dialogOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}
          onClick={() => setDialogOpen(false)}>
          <div onClick={e => e.stopPropagation()} style={{ background: 'white', borderRadius: 16, padding: 24, width: 360, boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>{lang === 'zh' ? '新建合集' : 'New Collection'}</h3>
            <input value={newName} onChange={e => setNewName(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleCreate()}
              placeholder={lang === 'zh' ? '合集名称' : 'Collection name'}
              autoFocus
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid var(--gray-200)', fontSize: 14, fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box', marginBottom: 16 }} />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost" onClick={() => setDialogOpen(false)}>{lang === 'zh' ? '取消' : 'Cancel'}</button>
              <button className="btn btn-primary" onClick={handleCreate}>{lang === 'zh' ? '创建' : 'Create'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Notes list for selected collection */}
      {selectedCol && (
        <div className="card">
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>
            {collections.find(c => c.id === selectedCol)?.name} - {lang === 'zh' ? '笔记列表' : 'Notes'}
          </h3>
          {notes.filter(n => collections.find(c => c.id === selectedCol)?.noteIds.includes(n.task_id)).map(n => (
            <div key={n.task_id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--gray-100)' }}>
              <span style={{ flex: 1, fontSize: 13, cursor: 'pointer' }} onClick={() => navigate('/note/' + n.task_id)}>{n.videoName}</span>
              <button className="btn btn-ghost btn-sm" style={{ padding: 4 }}
                onClick={() => removeFromCollection(selectedCol, n.task_id)}>
                <Trash2 size={13} color="var(--gray-400)" />
              </button>
            </div>
          ))}
          {notes.filter(n => !collections.find(c => c.id === selectedCol)?.noteIds.includes(n.task_id)).length > 0 && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--gray-200)' }}>
              <div style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 8 }}>{lang === 'zh' ? '添加笔记到合集' : 'Add notes to collection'}</div>
              {notes.filter(n => !collections.find(c => c.id === selectedCol)?.noteIds.includes(n.task_id)).slice(0, 10).map(n => (
                <div key={n.task_id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0' }}>
                  <span style={{ flex: 1, fontSize: 12, color: 'var(--gray-500)' }}>{n.videoName}</span>
                  <button className="btn btn-ghost btn-sm" style={{ padding: '2px 8px', fontSize: 11 }}
                    onClick={() => addToCollection(selectedCol, n.task_id)}>
                    <Plus size={12} /> {lang === 'zh' ? '添加' : 'Add'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
