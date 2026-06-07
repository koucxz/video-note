import { useState, useEffect, useCallback } from 'react'
import { X, CheckCircle2, AlertTriangle, Info } from 'lucide-react'

const ICONS = { success: CheckCircle2, error: AlertTriangle, info: Info }
const COLORS = { success: 'var(--green)', error: 'var(--red)', info: 'var(--blue)' }
const BGS = { success: '#ecfdf5', error: '#fef2f2', info: '#eff6ff' }

export default function Toast({ toasts, onRemove }) {
  return (
    <div style={{ position: 'fixed', top: 68, right: 20, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 380 }}>
      {toasts.map(t => (
        <ToastItem key={t.id} toast={t} onRemove={onRemove} />
      ))}
    </div>
  )
}

function ToastItem({ toast, onRemove }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => { requestAnimationFrame(() => setVisible(true)) }, [])
  useEffect(() => {
    const timer = setTimeout(() => { setVisible(false); setTimeout(() => onRemove(toast.id), 300) }, toast.duration || 4000)
    return () => clearTimeout(timer)
  }, [toast.id, toast.duration, onRemove])

  const Icon = ICONS[toast.type] || Info
  const color = COLORS[toast.type] || COLORS.info
  const bg = BGS[toast.type] || BGS.info

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '10px 14px', borderRadius: 10,
      background: bg, border: `1px solid ${color}30`,
      boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
      transform: visible ? 'translateX(0)' : 'translateX(120%)',
      opacity: visible ? 1 : 0,
      transition: 'all 0.3s ease',
    }}>
      <Icon size={16} color={color} style={{ flexShrink: 0, marginTop: 1 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        {toast.title && <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-800)', marginBottom: 2 }}>{toast.title}</div>}
        <div style={{ fontSize: 12, color: 'var(--gray-500)', lineHeight: 1.4 }}>{typeof toast.message === 'object' ? JSON.stringify(toast.message) : toast.message}</div>
      </div>
      <button onClick={() => onRemove(toast.id)}
        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, display: 'flex', color: 'var(--gray-400)' }}>
        <X size={14} />
      </button>
    </div>
  )
}