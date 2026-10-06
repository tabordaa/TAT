import { useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'
import { IconCheck, IconInfo, IconLock, IconSave, IconUserPlus, IconUsers } from '../components/Icons'
import { validateEmployee } from '../features/employees/validateEmployee'
import {
  CONTRACT_TYPES,
  CONTRACTS_WITH_END_DATE,
  DOCUMENT_TYPES,
  type EmployeeFormErrors,
  type EmployeeFormValues,
} from '../types/employee'

const INITIAL_VALUES: EmployeeFormValues = {
  firstNames: '',
  lastNames: '',
  documentType: '',
  documentNumber: '',
  email: '',
  phone: '',
  position: '',
  area: '',
  contractType: '',
  startDate: '',
  endDate: '',
}

interface FieldProps {
  id: keyof EmployeeFormValues
  label: string
  required?: boolean
  hint?: string
  help?: string
  error?: string
  children: ReactNode
}

function Field({ id, label, required = false, hint, help, error, children }: FieldProps) {
  return (
    <div className={`field${error !== undefined ? ' field-invalid' : ''}`}>
      <div className="field-label-row">
        <label htmlFor={id}>
          {label}
          {required && <span className="required"> *</span>}
        </label>
        {hint !== undefined && <span className="field-hint">{hint}</span>}
      </div>
      {children}
      {error !== undefined ? (
        <p className="field-error" id={`${id}-error`}>
          {error}
        </p>
      ) : (
        help !== undefined && <p className="field-help">{help}</p>
      )}
    </div>
  )
}

export function RegisterEmployeePage() {
  const navigate = useNavigate()
  const [values, setValues] = useState<EmployeeFormValues>(INITIAL_VALUES)
  const [errors, setErrors] = useState<EmployeeFormErrors>({})
  const [isValidated, setIsValidated] = useState(false)

  function handleChange(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const name = event.target.name as keyof EmployeeFormValues
    setValues((prev) => ({ ...prev, [name]: event.target.value }))
    // Clear the error of the field being edited.
    setErrors((prev) => ({ ...prev, [name]: undefined }))
    setIsValidated(false)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const validationErrors = validateEmployee(values)
    setErrors(validationErrors)
    // TODO(HU-2.1 BE): POST /employees and map a 409 to
    // errors.documentNumber = 'Ya existe un empleado con este número de documento.'
    setIsValidated(Object.keys(validationErrors).length === 0)
  }

  const needsEndDate =
    values.contractType !== '' && CONTRACTS_WITH_END_DATE.includes(values.contractType)

  const describedBy = (id: keyof EmployeeFormValues) =>
    errors[id] !== undefined ? `${id}-error` : undefined

  return (
    <section>
      <nav className="breadcrumb-nav" aria-label="Ruta">
        <Link to="/empleados">
          <IconUsers size={16} /> Empleados
        </Link>
        <span aria-hidden="true">›</span>
        <strong>Registrar nuevo empleado</strong>
      </nav>

      <div className="page-header">
        <div className="page-header-title">
          <span className="page-icon" aria-hidden="true">
            <IconUserPlus size={22} />
          </span>
          <div>
            <h1 className="page-title">Registrar empleado</h1>
            <p className="page-subtitle">
              Ingresa la información personal y contractual para dar de alta al colaborador.
            </p>
          </div>
        </div>
      </div>

      <form className="card form-card" onSubmit={handleSubmit} noValidate>
        <div className="form-section-header">
          <p className="section-kicker">SECCIÓN 01</p>
          <h2>Datos personales</h2>
          <p className="muted">Información de identidad y contacto del trabajador.</p>
        </div>

        <div className="form-grid">
          <Field id="firstNames" label="Nombres" required hint="Según documento oficial" error={errors.firstNames}>
            <input id="firstNames" name="firstNames" value={values.firstNames} onChange={handleChange} aria-invalid={errors.firstNames !== undefined} aria-describedby={describedBy('firstNames')} />
          </Field>
          <Field id="lastNames" label="Apellidos" required hint="Paterno y materno" error={errors.lastNames}>
            <input id="lastNames" name="lastNames" value={values.lastNames} onChange={handleChange} aria-invalid={errors.lastNames !== undefined} aria-describedby={describedBy('lastNames')} />
          </Field>
          <Field id="documentType" label="Tipo de documento" required error={errors.documentType}>
            <select id="documentType" name="documentType" value={values.documentType} onChange={handleChange} aria-invalid={errors.documentType !== undefined} aria-describedby={describedBy('documentType')}>
              <option value="">Selecciona…</option>
              {Object.entries(DOCUMENT_TYPES).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field id="documentNumber" label="Número de documento" required error={errors.documentNumber}>
            <input id="documentNumber" name="documentNumber" value={values.documentNumber} onChange={handleChange} aria-invalid={errors.documentNumber !== undefined} aria-describedby={describedBy('documentNumber')} />
          </Field>
          <Field id="email" label="Correo electrónico" help="Para notificaciones oficiales." error={errors.email}>
            <input id="email" name="email" type="email" placeholder="correo.corporativo@empresa.com" value={values.email} onChange={handleChange} aria-invalid={errors.email !== undefined} aria-describedby={describedBy('email')} />
          </Field>
          <Field id="phone" label="Teléfono" help="Incluye el indicativo del país.">
            <input id="phone" name="phone" type="tel" placeholder="+57 300 123 4567" value={values.phone} onChange={handleChange} />
          </Field>
        </div>

        <hr className="divider" />

        <div className="form-section-header">
          <p className="section-kicker">SECCIÓN 02</p>
          <h2>Datos laborales</h2>
          <p className="muted">Cargo, área y condiciones del contrato.</p>
        </div>

        <div className="form-grid">
          <Field id="position" label="Cargo" required error={errors.position}>
            <input id="position" name="position" placeholder="Ej. Analista de Selección" value={values.position} onChange={handleChange} aria-invalid={errors.position !== undefined} aria-describedby={describedBy('position')} />
          </Field>
          <Field id="area" label="Área / Departamento">
            <input id="area" name="area" placeholder="Ej. Recursos Humanos" value={values.area} onChange={handleChange} />
          </Field>
          <Field id="contractType" label="Tipo de contrato" required error={errors.contractType}>
            <select id="contractType" name="contractType" value={values.contractType} onChange={handleChange} aria-invalid={errors.contractType !== undefined} aria-describedby={describedBy('contractType')}>
              <option value="">Selecciona…</option>
              {Object.entries(CONTRACT_TYPES).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field id="startDate" label="Fecha de inicio" required help="Día efectivo de alta laboral." error={errors.startDate}>
            <input id="startDate" name="startDate" type="date" value={values.startDate} onChange={handleChange} aria-invalid={errors.startDate !== undefined} aria-describedby={describedBy('startDate')} />
          </Field>
          <Field
            id="endDate"
            label={needsEndDate ? 'Fecha de finalización' : 'Fecha de finalización (opcional)'}
            required={needsEndDate}
            hint="Condicional"
            help="Aplica para contratos a término fijo, obra o aprendizaje."
            error={errors.endDate}
          >
            <input id="endDate" name="endDate" type="date" min={values.startDate || undefined} value={values.endDate} onChange={handleChange} aria-invalid={errors.endDate !== undefined} aria-describedby={describedBy('endDate')} />
          </Field>
          <div className="field">
            <div className="field-label-row">
              <span className="field-static-label">Estado del empleado</span>
            </div>
            <div className="input-readonly">
              <span className="badge badge-success">● ACTIVO</span>
              <span className="muted">Asignado por política</span>
              <IconLock size={16} />
            </div>
            <p className="field-help field-help-ok">
              <IconCheck size={14} /> Todo nuevo registro ingresa automáticamente como ACTIVO.
            </p>
          </div>
        </div>

        {isValidated && (
          <div className="alert alert-info" role="status">
            <IconInfo size={20} />
            <div className="alert-body">
              <strong>Formulario válido.</strong>
              <span>El guardado se conecta al API en la siguiente tarea (HU-2.1 backend).</span>
            </div>
          </div>
        )}

        <div className="form-footer">
          <p className="muted">
            <span className="required">*</span> Campos obligatorios.
          </p>
          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/empleados')}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary">
              <IconSave /> Guardar empleado
            </button>
          </div>
        </div>
      </form>
    </section>
  )
}
