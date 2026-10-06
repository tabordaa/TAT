import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router'
import axios from 'axios'
import { useAuth } from '../auth/useAuth'
import { BrandLogo } from '../components/BrandLogo'
import { IconAlert, IconClose, IconEye, IconEyeOff, IconLock } from '../components/Icons'

interface LoginError {
  title: string
  detail: string
}

function toLoginError(error: unknown): LoginError {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 401) {
      return {
        title: 'Correo o contraseña incorrectos.',
        detail: 'Verifica tus credenciales e intenta de nuevo.',
      }
    }
    if (error.response?.status === 422) {
      return { title: 'Datos inválidos.', detail: 'Revisa el formato del correo electrónico.' }
    }
  }
  return {
    title: 'No pudimos conectar con el servidor.',
    detail: 'Intenta de nuevo en unos segundos.',
  }
}

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<LoginError | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (user !== null) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login({ email: email.trim(), password })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(toLoginError(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={(e) => void handleSubmit(e)} noValidate>
        <div className="login-header">
          <BrandLogo />
          <h1 className="login-title">TAT</h1>
          <p className="login-subtitle">Inicia sesión para gestionar el talento de tu empresa</p>
        </div>

        <div className="field">
          <div className="field-label-row">
            <label htmlFor="email">Correo electrónico</label>
            <span className="field-hint">(Obligatorio)</span>
          </div>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="nombre@empresa.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="field">
          <div className="field-label-row">
            <label htmlFor="password">Contraseña</label>
          </div>
          <div className="input-with-action">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="input-action"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            >
              {showPassword ? <IconEyeOff /> : <IconEye />}
            </button>
          </div>
        </div>

        {error !== null && (
          <div className="alert alert-error" role="alert">
            <IconAlert size={20} />
            <div className="alert-body">
              <strong>{error.title}</strong>
              <span>{error.detail}</span>
            </div>
            <button
              type="button"
              className="alert-close"
              onClick={() => setError(null)}
              aria-label="Cerrar alerta"
            >
              <IconClose size={16} />
            </button>
          </div>
        )}

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={isSubmitting || email === '' || password === ''}
        >
          {isSubmitting ? 'Ingresando…' : 'Iniciar sesión'}
        </button>

        <hr className="divider" />

        <p className="login-note">
          <IconLock size={18} />
          Las cuentas son gestionadas exclusivamente por el administrador de sistemas de la empresa.
        </p>
      </form>

      <footer className="login-footer">
        TAT · Tracking and Talent © {new Date().getFullYear()}. Todos los derechos reservados.
      </footer>
    </div>
  )
}
