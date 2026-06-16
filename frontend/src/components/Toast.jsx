import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const COLORS = {
  success: { bg: 'bg-clear-surface', border: 'border-clear-border', text: 'text-clear', icon: '#16A34A' },
  error:   { bg: 'bg-alarm-surface', border: 'border-alarm-border', text: 'text-alarm', icon: '#DC2626' },
  warning: { bg: 'bg-caution-surface', border: 'border-caution-border', text: 'text-caution', icon: '#D97706' },
  info:    { bg: 'bg-indigo-surface', border: 'border-indigo-border', text: 'text-indigo', icon: '#4F46E5' },
}

function Toast({ id, type, title, message, onRemove }) {
  const [exiting, setExiting] = useState(false)
  const Icon = ICONS[type] || ICONS.info
  const color = COLORS[type] || COLORS.info

  useEffect(() => {
    const timer = setTimeout(() => {
      setExiting(true)
      setTimeout(() => onRemove(id), 250)
    }, 4500)
    return () => clearTimeout(timer)
  }, [id, onRemove])

  function handleDismiss() {
    setExiting(true)
    setTimeout(() => onRemove(id), 250)
  }

  return (
    <div className={`
      flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-sm
      ${color.bg} ${color.border}
      ${exiting ? 'animate-toast-out' : 'animate-toast-in'}
      max-w-[420px] w-full
    `}>
      <Icon size={18} color={color.icon} className="shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        {title && <div className="text-heading text-text-primary mb-0.5">{title}</div>}
        <div className="text-body text-text-secondary leading-relaxed">{message}</div>
      </div>
      <button onClick={handleDismiss} className="shrink-0 p-0.5 rounded hover:bg-black/5 transition-colors">
        <X size={14} className="text-text-ghost" />
      </button>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((type, message, title) => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, type, title, message }])
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = useCallback({
    success: (msg, title) => addToast('success', msg, title),
    error: (msg, title) => addToast('error', msg, title),
    warning: (msg, title) => addToast('warning', msg, title),
    info: (msg, title) => addToast('info', msg, title),
  }, [addToast])

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {/* Toast Container */}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-auto">
        {toasts.map(t => (
          <Toast key={t.id} {...t} onRemove={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
