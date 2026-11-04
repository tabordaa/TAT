import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router'
import axios from 'axios'
import { useAuth } from '../auth/useAuth'
import { BrandLogo } from '../components/BrandLogo'
import { IconAlert, IconClose, IconEye, IconEyeOff } from '../components/Icons'

const MIN_LENGTH = 8 // same limit as the API
const MAX_LENGTH = 128

interface FormErrors {
  currentPassword?: string
  newPassword?: string
  confirmation?: string
  general?: string
}

function validate(current: string, next: string, confirmation: string): FormErrors {
  const errors: FormErrors = {}
  if (current === '') errors.currentPassword = 'Ingresa tu contraseña actual.'
  if (next.length < MIN_LENGTH) {
    errors.newPassword = `La nueva contraseña debe tener al menos ${MIN_LENGTH} caracteres.`
  } else if (next === current) {
    errors.newPassword = 'La nueva contraseña debe ser distinta de la actual.'
  }
  if (confirmation !== next) errors.confirmation = 'Las contraseñas no coinciden.'
  return errors
}

function toServerErrors(error: unknown): FormErrors {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    if (status === 429) {
      return { general: 'Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo.' }
    }
    if (status === 400) {
      const detail: unknown = error.response?.data?.detail
      if (typeof detail === 'object' && detail !== null && 'field' in detail) {
        return detail.field === 'current_password'
          ? { currentPassword: 'La contraseña actual es incorrecta.' }
          : { newPassword: 'La nueva contraseña debe ser distinta de la actual.' }
      }
    }
    if (status === 422) {
      return { newPassword: `Debe tener entre ${MIN_LENGTH} y ${MAX_LENGTH} caracteres.` }
    }
  }
  return { general: 'No pudimos conectar con el servidor. Intenta de nuevo en unos segundos.' }
}

// HU-1.2: the only screen a session with a temporary password can open.
export function ChangePasswordPage() {
  const { user, changePassword, logout } = useAuth()
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [showPasswords, setShowPasswords] = useState(false)
  const [errors, setErrors] = useState<FormErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (user === null) {
    return <Navigate to="/login" replace />
  }

  const isForced = user.must_change_password
  const inputType = showPasswords ? 'text' : 'password'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = validate(currentPassword, newPassword, confirmation)
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setIsSubmitting(true)
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword })
      navigate('/', { replace: true })
    } catch (err) {
      setErrors(toServerErrors(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={(e) => void handleSubmit(e)} noValidate>
        <div className="login-header">
          <BrandLogo />
          <h1 className="login-title">Cambia tu contraseña</h1>
          <p className="login-subtitle">
            {isForced
              ? 'Recibiste una contraseña temporal. Crea una propia para continuar: solo tú debes conocerla.'
              : 'Elige una contraseña nueva para tu cuenta.'}
          </p>
        </div>

        <div className="field">
          <div className="field-label-row">
            <label htmlFor="current-password">
              {isForced ? 'Contraseña temporal' : 'Contraseña actual'}
            </label>
          </div>
          <input
            id="current-password"
            type={inputType}
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            aria-invalid={errors.currentPassword !== undefined}
            aria-describedby="current-password-error"
            required
          />
          {errors.currentPassword !== undefined && (
            <p id="current-password-error" className="field-error">
              {errors.currentPassword}
            </p>
          )}
        </div>

        <div className="field">
          <div className="field-label-row">
            <label htmlFor="new-password">Nueva contraseña</label>
            <span className="field-hint">(Mínimo {MIN_LENGTH} caracteres)</span>
          </div>
          <div className="input-with-action">
            <input
              id="new-password"
              type={inputType}
              autoComplete="new-password"
              maxLength={MAX_LENGTH}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              aria-invalid={errors.newPassword !== undefined}
              aria-describedby="new-password-error"
              required
            />
            <button
              type="button"
              className="input-action"
              onClick={() => setShowPasswords((v) => !v)}
              aria-label={showPasswords ? 'Ocultar contraseñas' : 'Mostrar contraseñas'}
            >
              {showPasswords ? <IconEyeOff /> : <IconEye />}
            </button>
          </div>
          {errors.newPassword !== undefined && (
            <p id="new-password-error" className="field-error">
              {errors.newPassword}
            </p>
          )}
        </div>

        <div className="field">
          <div className="field-label-row">
            <label htmlFor="confirm-password">Confirma la nueva contraseña</label>
          </div>
          <input
            id="confirm-password"
            type={inputType}
            autoComplete="new-password"
            maxLength={MAX_LENGTH}
            value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
            aria-invalid={errors.confirmation !== undefined}
            aria-describedby="confirm-password-error"
            required
          />
          {errors.confirmation !== undefined && (
            <p id="confirm-password-error" className="field-error">
              {errors.confirmation}
            </p>
          )}
        </div>

        {errors.general !== undefined && (
          <div className="alert alert-error" role="alert">
            <IconAlert size={20} />
            <div className="alert-body">
              <span>{errors.general}</span>
            </div>
            <button
              type="button"
              className="alert-close"
              onClick={() => setErrors({})}
              aria-label="Cerrar alerta"
            >
              <IconClose size={16} />
            </button>
          </div>
        )}

        <button type="submit" className="btn btn-primary btn-block" disabled={isSubmitting}>
          {isSubmitting ? 'Guardando…' : 'Guardar contraseña'}
        </button>

        <button
          type="button"
          className="btn btn-secondary btn-block"
          onClick={() => {
            if (isForced) {
              void logout().then(() => navigate('/login', { replace: true }))
            } else {
              navigate(-1)
            }
          }}
        >
          {isForced ? 'Cerrar sesión' : 'Cancelar'}
        </button>
      </form>
    </div>
  )
}
