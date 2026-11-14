import { createContext, useContext, useState, useCallback, useRef } from 'react'
import Toast from '../components/Toast'

const ToastContext = createContext()

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const recentToasts = useRef(new Map())

  const addToast = useCallback((type, message, title, duration) => {
    const key = `${type}:${title || ''}:${String(message)}`
    const now = Date.now()
    const previous = recentToasts.current.get(key) || 0
    if (now - previous < 2500) return
    recentToasts.current.set(key, now)
    for (const [toastKey, timestamp] of recentToasts.current) {
      if (now - timestamp > 5000) recentToasts.current.delete(toastKey)
    }
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, type, message, title, duration }])
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = {
    success: (msg, title) => addToast('success', msg, title),
    error: (msg, title) => addToast('error', msg, title),
    info: (msg, title) => addToast('info', msg, title),
  }

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <Toast toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
