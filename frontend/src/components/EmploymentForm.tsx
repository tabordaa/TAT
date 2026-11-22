import { useState, type FormEvent } from 'react'
import axios from 'axios'
import { updateEmployment } from '../api/employees'
import type { Employee, EmploymentUpdatePayload } from '../types/employee'
import { IconAlert, IconCheck } from './Icons'

// Same limits as the API (EmploymentUpdate) and the registration form.
const MAX_TEXT_LENGTH = 120
const SALARY_PATTERN = /^\d{1,10}(\.\d{1,2})?$/

interface Values {
  position: string
  area: string
  salary: string
}

type Errors = Partial<Record<keyof Values, string>>

function validate(values: Values): Errors {
  const errors: Errors = {}
  const required = 'Este campo es obligatorio.'
  if (values.position.trim() === '') errors.position = required
  if (values.area.trim() === '') errors.area = required
  const salary = values.salary.trim()
  if (salary === '') {
    errors.salary = required
  } else if (!SALARY_PATTERN.test(salary)) {
    errors.salary = 'Usa solo números, con máximo 2 decimales (ej. 2500000.50).'
  } else if (Number(salary) <= 0) {
    errors.salary = 'Debe ser mayor que cero.'
  }
  return errors
}

/** Only what really changed goes to the API: the server logs each field it receives. */
function changedFields(employee: Employee, values: Values): EmploymentUpdatePayload {
  const payload: EmploymentUpdatePayload = {}
  if (values.position.trim() !== employee.position) payload.position = values.position.trim()
  if (values.area.trim() !== employee.area) payload.area = values.area.trim()
  if (Number(values.salary.trim()) !== Number(employee.salary)) payload.salary = values.salary.trim()
  return payload
}

function toMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 409) return 'Solo se pueden editar los datos de un empleado activo.'
    if (error.response?.status === 403) return 'No tienes permiso para realizar esta acción.'
    if (error.response?.status === 422) return 'El servidor rechazó algunos datos. Revisa el formulario.'
  }
  return 'No se pudieron guardar los cambios. Inténtalo de nuevo.'
}

interface EmploymentFormProps {
  employee: Employee
  onSaved: () => void
}

// HU-2.4: rendered only for ADMIN and HR on an active employee. The API enforces the same.
export function EmploymentForm({ employee, onSaved }: EmploymentFormProps) {
  const initial: Values = {
    position: employee.position,
    area: employee.area,
    salary: employee.salary,
  }
  const [isOpen, setIsOpen] = useState(false)
  const [values, setValues] = useState<Values>(initial)
  const [errors, setErrors] = useState<Errors>({})
  const [message, setMessage] = useState<{ kind: 'error' | 'info'; text: string } | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  function open() {
    setValues(initial)
    setErrors({})
    setMessage(null)
    setIsOpen(true)
  }

  function change(field: keyof Values, value: string) {
    setValues((previous) => ({ ...previous, [field]: value }))
    setErrors((previous) => ({ ...previous, [field]: undefined }))
    setMessage(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = validate(values)
    setErrors(found)
    if (Object.keys(found).length > 0) return

    const payload = changedFields(employee, values)
    if (Object.keys(payload).length === 0) {
      setMessage({ kind: 'info', text: 'No hay cambios para guardar.' })
      return
    }

    setIsSaving(true)
    try {
      await updateEmployment(employee.id, payload)
      setIsOpen(false)
      onSaved()
    } catch (error) {
      setMessage({ kind: 'error', text: toMessage(error) })
    } finally {
      setIsSaving(false)
    }
  }

  if (!isOpen) {
    return (
      <div className="form-actions">
        <button type="button" className="btn btn-secondary" onClick={open}>
          Editar datos laborales
        </button>
      </div>
    )
  }

  const describedBy = (field: keyof Values) =>
    errors[field] !== undefined ? `employment-${field}-error` : undefined

  return (
    <form
      className="inline-edit-form"
      aria-labelledby="employment-form-title"
      onSubmit={(event) => void handleSubmit(event)}
      noValidate
    >
      <h2 id="employment-form-title" className="section-kicker">
        EDITAR DATOS LABORALES
      </h2>
      <p className="muted">
        Un cambio de salario queda en el historial salarial y en la auditoría.
      </p>

      {message !== null && (
        <div
          className={message.kind === 'error' ? 'alert alert-error' : 'alert alert-info'}
          role={message.kind === 'error' ? 'alert' : 'status'}
        >
          {message.kind === 'error' ? <IconAlert size={20} /> : <IconCheck size={20} />}
          <div className="alert-body">
            <span>{message.text}</span>
          </div>
        </div>
      )}

      <div className="form-grid">
        <div className={`field${errors.position !== undefined ? ' field-invalid' : ''}`}>
          <div className="field-label-row">
            <label htmlFor="employment-position">Cargo</label>
          </div>
          <input
            id="employment-position"
            maxLength={MAX_TEXT_LENGTH}
            value={values.position}
            onChange={(event) => change('position', event.target.value)}
            aria-invalid={errors.position !== undefined}
            aria-describedby={describedBy('position')}
          />
          {errors.position !== undefined && (
            <p className="field-error" id="employment-position-error">
              {errors.position}
            </p>
          )}
        </div>

        <div className={`field${errors.area !== undefined ? ' field-invalid' : ''}`}>
          <div className="field-label-row">
            <label htmlFor="employment-area">Área / Departamento</label>
          </div>
          <input
            id="employment-area"
            maxLength={MAX_TEXT_LENGTH}
            value={values.area}
            onChange={(event) => change('area', event.target.value)}
            aria-invalid={errors.area !== undefined}
            aria-describedby={describedBy('area')}
          />
          {errors.area !== undefined && (
            <p className="field-error" id="employment-area-error">
              {errors.area}
            </p>
          )}
        </div>

        <div className={`field${errors.salary !== undefined ? ' field-invalid' : ''}`}>
          <div className="field-label-row">
            <label htmlFor="employment-salary">Salario mensual (COP)</label>
          </div>
          <input
            id="employment-salary"
            inputMode="decimal"
            value={values.salary}
            onChange={(event) => change('salary', event.target.value)}
            aria-invalid={errors.salary !== undefined}
            aria-describedby={describedBy('salary')}
          />
          {errors.salary !== undefined ? (
            <p className="field-error" id="employment-salary-error">
              {errors.salary}
            </p>
          ) : (
            <p className="field-help">Sin puntos de miles; usa punto para decimales.</p>
          )}
        </div>
      </div>

      <div className="form-actions">
        <button
          type="button"
          className="btn btn-secondary"
          disabled={isSaving}
          onClick={() => setIsOpen(false)}
        >
          Cancelar
        </button>
        <button type="submit" className="btn btn-primary" disabled={isSaving}>
          {isSaving ? 'Guardando…' : 'Guardar datos laborales'}
        </button>
      </div>
    </form>
  )
}
