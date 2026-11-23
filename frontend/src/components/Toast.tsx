import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { IconCheck, IconClose, IconInfo } from './Icons'

export type ToastKind = 'success' | 'info'

interface ToastRecord {
  id: number
  message: string
  kind: ToastKind
}

interface ToastContextValue {
  showToast: (message: string, kind?: ToastKind) => void
}

const TOAST_DURATION_MS = 4000
const MAX_TOASTS = 3

const ToastContext = createContext<ToastContextValue | null>(null)

interface ToastItemProps {
  toast: ToastRecord
  onDismiss: (id: number) => void
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
  const [isPaused, setIsPaused] = useState(false)
  const remainingRef = useRef(TOAST_DURATION_MS)
  const startedAtRef = useRef(0)

  useEffect(() => {
    if (isPaused) return
    startedAtRef.current = Date.now()
    const timeoutId = window.setTimeout(() => onDismiss(toast.id), remainingRef.current)
    return () => window.clearTimeout(timeoutId)
  }, [isPaused, onDismiss, toast.id])

  function handleMouseEnter() {
    if (isPaused) return
    const elapsed = Date.now() - startedAtRef.current
    remainingRef.current = Math.max(0, remainingRef.current - elapsed)
    setIsPaused(true)
  }

  function handleMouseLeave() {
    if (!isPaused) return
    setIsPaused(false)
  }

  return (
    <div
      className={`toast toast-${toast.kind}`}
      role="status"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <span className="toast-icon" aria-hidden="true">
        {toast.kind === 'info' ? <IconInfo size={18} /> : <IconCheck size={18} />}
      </span>
      <span className="toast-message">{toast.message}</span>
      <button
        type="button"
        className="toast-close"
        aria-label="Cerrar aviso"
        onClick={() => onDismiss(toast.id)}
      >
        <IconClose size={16} />
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([])
  const nextIdRef = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((previous) => previous.filter((item) => item.id !== id))
  }, [])

  const showToast = useCallback((message: string, kind: ToastKind = 'success') => {
    const id = nextIdRef.current
    nextIdRef.current += 1
    setToasts((previous) => [...previous.slice(-(MAX_TOASTS - 1)), { id, message, kind }])
  }, [])

  const value = useMemo<ToastContextValue>(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Pre-mounted live region so assistive tech announces newly inserted status items. */}
      <div className="toast-region" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (context === null) {
    throw new Error('useToast must be used inside ToastProvider')
  }
  return context
}
