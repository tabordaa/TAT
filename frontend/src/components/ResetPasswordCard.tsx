import { useState } from 'react'
import axios from 'axios'
import { resetAccountPassword } from '../api/employees'
import type { AccountCreated, Employee } from '../types/employee'
import { IconAlert, IconLock } from './Icons'
import { TemporaryPasswordPanel } from './TemporaryPasswordPanel'

type Step =
  | { name: 'idle' }
  | { name: 'confirming' }
  | { name: 'saving' }
  | { name: 'done'; account: AccountCreated }
  | { name: 'error'; message: string }

function toMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 409) {
      const detail: unknown = error.response.data?.detail
      if (typeof detail === 'object' && detail !== null && 'field' in detail) {
        return detail.field === 'status'
          ? 'Un empleado inactivo no puede tener acceso al sistema.'
          : 'Para tu propia cuenta usa la opción de cambiar contraseña.'
      }
    }
    if (error.response?.status === 404) return 'Este empleado ya no tiene cuenta de acceso.'
    if (error.response?.status === 403) return 'No tienes permiso para realizar esta acción.'
  }
  return 'No se pudo restablecer la contraseña. Inténtalo de nuevo.'
}

// HU-1.5: rendered only for administrators. The API enforces the same rule.
export function ResetPasswordCard({ employee }: { employee: Employee }) {
  const [step, setStep] = useState<Step>({ name: 'idle' })
  const fullName = `${employee.first_names} ${employee.last_names}`

  async function handleConfirm() {
    setStep({ name: 'saving' })
    try {
      setStep({ name: 'done', account: await resetAccountPassword(employee.id) })
    } catch (error) {
      setStep({ name: 'error', message: toMessage(error) })
    }
  }

  if (step.name === 'done') {
    return (
      <TemporaryPasswordPanel
        title="Contraseña restablecida."
        description={`La contraseña anterior de ${fullName} ya no funciona y sus sesiones se cerraron.`}
        continueLabel="Entendido"
        account={step.account}
        onContinue={() => setStep({ name: 'idle' })}
      />
    )
  }

  return (
    <div className="card detail-section">
      <p className="section-kicker">ACCESO AL SISTEMA</p>

      {step.name === 'error' && (
        <div className="alert alert-error" role="alert">
          <IconAlert size={20} />
          <div className="alert-body">
            <span>{step.message}</span>
          </div>
        </div>
      )}

      {step.name === 'confirming' || step.name === 'saving' ? (
        <>
          <p>
            ¿Restablecer la contraseña de <strong>{fullName}</strong>? Su contraseña actual dejará de
            funcionar y deberá crear una nueva al ingresar.
          </p>
          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={step.name === 'saving'}
              onClick={() => setStep({ name: 'idle' })}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={step.name === 'saving'}
              onClick={() => void handleConfirm()}
            >
              {step.name === 'saving' ? 'Restableciendo…' : 'Sí, restablecer'}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="muted">
            Genera una contraseña temporal si el empleado olvidó sus credenciales.
          </p>
          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setStep({ name: 'confirming' })}
            >
              <IconLock /> Restablecer contraseña
            </button>
          </div>
        </>
      )}
    </div>
  )
}
