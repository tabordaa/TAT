import { useState } from 'react'
import { IconAlert, IconCheck, IconLock } from './Icons'
import { ROLE_LABELS } from '../types/auth'
import type { AccountCreated } from '../types/employee'

interface TemporaryPasswordPanelProps {
  employeeName: string
  account: AccountCreated
  onContinue: () => void
}

type CopyState = 'idle' | 'copied' | 'failed'

/**
 * Shows the temporary password of a brand-new account.
 *
 * It exists only in this component's props (React memory): never in the URL,
 * router state, localStorage or sessionStorage. Once the admin leaves the
 * screen it is gone for good, because the server keeps only its hash.
 */
export function TemporaryPasswordPanel({
  employeeName,
  account,
  onContinue,
}: TemporaryPasswordPanelProps) {
  const [copyState, setCopyState] = useState<CopyState>('idle')

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(account.temporary_password)
      setCopyState('copied')
    } catch {
      // Clipboard can be blocked (insecure context, permissions): the admin can still select it by hand.
      setCopyState('failed')
    }
  }

  return (
    <div className="card form-card" aria-live="polite">
      <div className="alert alert-success" role="status">
        <IconCheck size={20} />
        <div className="alert-body">
          <strong>Empleado registrado y cuenta de acceso creada.</strong>
          <span>{employeeName} ya puede ingresar con las credenciales de abajo.</span>
        </div>
      </div>

      <dl className="detail-grid">
        <div className="detail-item">
          <dt>Usuario (correo)</dt>
          <dd>{account.email}</dd>
        </div>
        <div className="detail-item">
          <dt>Rol</dt>
          <dd>{ROLE_LABELS[account.role]}</dd>
        </div>
        <div className="detail-item">
          <dt>Contraseña temporal</dt>
          <dd>
            <code className="secret-value">
              {account.temporary_password}
            </code>
          </dd>
        </div>
      </dl>

      <div className="alert alert-info" role="note">
        <IconLock size={20} />
        <div className="alert-body">
          <strong>Esta contraseña se muestra una sola vez.</strong>
          <span>
            Cópiala y entrégala al empleado por un canal seguro. No se puede volver a consultar y
            deberá cambiarla en su primer ingreso.
          </span>
        </div>
      </div>

      {copyState === 'failed' && (
        <div className="alert alert-error" role="alert">
          <IconAlert size={20} />
          <div className="alert-body">
            <strong>No se pudo copiar automáticamente.</strong>
            <span>Selecciona la contraseña y cópiala manualmente antes de salir.</span>
          </div>
        </div>
      )}

      <div className="form-footer">
        <p className="muted">Al salir de esta pantalla la contraseña ya no podrá verse.</p>
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={() => void handleCopy()}>
            {copyState === 'copied' ? <IconCheck /> : null}
            {copyState === 'copied' ? 'Copiada' : 'Copiar contraseña'}
          </button>
          <button type="button" className="btn btn-primary" onClick={onContinue}>
            Entendido, ir al listado
          </button>
        </div>
      </div>
    </div>
  )
}
