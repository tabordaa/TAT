import { useEffect, useState, type FormEvent } from 'react'
import axios from 'axios'
import { assignContract, listContracts, terminateContract } from '../api/contracts'
import {
  CONTRACT_TYPES,
  CONTRACTS_WITH_END_DATE,
  type Contract,
  type ContractType,
  type Employee,
} from '../types/employee'
import { IconAlert } from './Icons'

const dateFormatter = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeZone: 'UTC' })

function formatDate(isoDate: string): string {
  return dateFormatter.format(new Date(`${isoDate}T00:00:00Z`))
}

/** "2026-01-15" in the user's local calendar: the most a departure date can be. */
function localToday(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

function isContractType(value: string): value is ContractType {
  return value in CONTRACT_TYPES
}

/** The server's structured conflict, translated; anything else gets the fallback. */
function toMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail
    if (typeof detail === 'object' && detail !== null && 'field' in detail) {
      switch (detail.field) {
        case 'document_number':
          return 'Otro empleado activo ya tiene este documento: no se puede reingresar.'
        case 'email':
          return 'Otro empleado activo ya tiene este correo: no se puede reingresar.'
        case 'start_date':
          return 'El nuevo contrato no puede iniciar antes que el anterior.'
        case 'end_date':
          return 'La fecha no puede ser anterior al inicio del contrato ni futura.'
        case 'status':
          return 'Este empleado ya está inactivo.'
        case 'account':
          return 'No puedes finalizar tu propio contrato.'
      }
    }
    if (error.response?.status === 403) return 'No tienes permiso para realizar esta acción.'
  }
  return fallback
}

interface AssignFormProps {
  employee: Employee
  onDone: () => void
}

// HU-3.1. CA02 and CA03: the end date is required or disabled depending on the type.
function AssignContractForm({ employee, onDone }: AssignFormProps) {
  const [contractType, setContractType] = useState<ContractType | ''>('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const isRehire = employee.status === 'INACTIVO'
  const needsEndDate = contractType !== '' && CONTRACTS_WITH_END_DATE.includes(contractType)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (contractType === '' || startDate === '') {
      setError('Selecciona el tipo de contrato y la fecha de inicio.')
      return
    }
    if (needsEndDate && endDate === '') {
      setError('La fecha de finalización es obligatoria para este tipo de contrato.')
      return
    }
    if (needsEndDate && endDate < startDate) {
      setError('La fecha de finalización no puede ser anterior a la de inicio.')
      return
    }

    setError(null)
    setIsSaving(true)
    try {
      await assignContract(employee.id, {
        contract_type: contractType,
        start_date: startDate,
        end_date: needsEndDate ? endDate : null,
      })
      onDone()
    } catch (err) {
      setError(toMessage(err, 'No se pudo guardar el contrato. Inténtalo de nuevo.'))
      setIsSaving(false)
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} noValidate>
      {isRehire && (
        <p className="muted">
          Al guardar, el empleado vuelve a estado Activo. Su acceso al sistema no se reactiva: un
          administrador debe restablecer su contraseña.
        </p>
      )}
      {error !== null && (
        <div className="alert alert-error" role="alert">
          <IconAlert size={20} />
          <div className="alert-body">
            <span>{error}</span>
          </div>
        </div>
      )}
      <div className="form-grid">
        <div className="field">
          <div className="field-label-row">
            <label htmlFor="contract-type">Tipo de contrato</label>
          </div>
          <select
            id="contract-type"
            value={contractType}
            onChange={(event) => {
              const value = event.target.value
              if (value === '' || isContractType(value)) {
                setContractType(value)
                if (value === '' || !CONTRACTS_WITH_END_DATE.includes(value)) setEndDate('')
              }
            }}
          >
            <option value="">Selecciona…</option>
            {(Object.keys(CONTRACT_TYPES) as ContractType[]).map((type) => (
              <option key={type} value={type}>
                {CONTRACT_TYPES[type]}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <div className="field-label-row">
            <label htmlFor="contract-start">Fecha de inicio</label>
          </div>
          <input
            id="contract-start"
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </div>
        <div className="field">
          <div className="field-label-row">
            <label htmlFor="contract-end">Fecha de finalización</label>
            {!needsEndDate && <span className="field-hint">(No aplica)</span>}
          </div>
          <input
            id="contract-end"
            type="date"
            min={startDate || undefined}
            value={endDate}
            disabled={!needsEndDate}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </div>
      </div>
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={isSaving}>
          {isSaving ? 'Guardando…' : isRehire ? 'Registrar reingreso' : 'Asignar contrato'}
        </button>
      </div>
    </form>
  )
}

interface TerminateModalProps {
  employee: Employee
  onCancel: () => void
  onDone: () => void
}

// HU-3.3 CA01: two explicit steps before the departure is applied.
function TerminateContractModal({ employee, onCancel, onDone }: TerminateModalProps) {
  const [step, setStep] = useState<'date' | 'confirm'>('date')
  const [endDate, setEndDate] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const fullName = `${employee.first_names} ${employee.last_names}`
  const maxDate = localToday()

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onCancel])

  function handleContinue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (endDate === '') {
      setError('Selecciona la fecha de salida.')
    } else if (endDate < employee.start_date) {
      setError('La fecha no puede ser anterior al inicio del contrato.')
    } else if (endDate > maxDate) {
      setError('La fecha de salida no puede ser futura.')
    } else {
      setError(null)
      setStep('confirm')
    }
  }

  async function handleConfirm() {
    setIsSaving(true)
    setError(null)
    try {
      await terminateContract(employee.id, endDate)
      onDone()
    } catch (err) {
      setError(toMessage(err, 'No se pudo registrar la baja. Inténtalo de nuevo.'))
      setStep('date')
      setIsSaving(false)
    }
  }

  return (
    <div className="modal-backdrop">
      <div
        className="card modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="terminate-title"
      >
        <h2 id="terminate-title">Finalizar contrato de {fullName}</h2>

        {error !== null && (
          <div className="alert alert-error" role="alert">
            <IconAlert size={20} />
            <div className="alert-body">
              <span>{error}</span>
            </div>
          </div>
        )}

        {step === 'date' ? (
          <form onSubmit={handleContinue} noValidate>
            <div className="field">
              <div className="field-label-row">
                <label htmlFor="terminate-date">Fecha de salida</label>
              </div>
              <input
                id="terminate-date"
                type="date"
                autoFocus
                min={employee.start_date}
                max={maxDate}
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </div>
            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={onCancel}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary">
                Continuar
              </button>
            </div>
          </form>
        ) : (
          <>
            <p>
              <strong>{fullName}</strong> quedará inactivo con fecha de salida{' '}
              <strong>{formatDate(endDate)}</strong>. Su cuenta se desactivará y sus sesiones se
              cerrarán de inmediato. Su información se conserva.
            </p>
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={isSaving}
                onClick={() => setStep('date')}
              >
                Volver
              </button>
              <button
                type="button"
                className="btn btn-danger"
                disabled={isSaving}
                onClick={() => void handleConfirm()}
              >
                {isSaving ? 'Registrando…' : 'Sí, finalizar contrato'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

interface ContractSectionProps {
  employee: Employee
  /** ADMIN and HR. A MANAGER sees the history but no actions; the API enforces the same. */
  canWrite: boolean
  onChanged: () => void
}

export function ContractSection({ employee, canWrite, onChanged }: ContractSectionProps) {
  const [contracts, setContracts] = useState<Contract[] | null>(null)
  const [loadFailed, setLoadFailed] = useState(false)
  const [isAssigning, setIsAssigning] = useState(false)
  const [isTerminating, setIsTerminating] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    setLoadFailed(false)
    listContracts(employee.id, controller.signal)
      .then(setContracts)
      .catch((error: unknown) => {
        if (!axios.isCancel(error)) setLoadFailed(true)
      })
    return () => controller.abort()
    // status and start_date change with every assignment or departure.
  }, [employee.id, employee.status, employee.start_date])

  function handleDone() {
    setIsAssigning(false)
    setIsTerminating(false)
    onChanged()
  }

  return (
    <div className="card detail-section">
      <p className="section-kicker">CONTRATOS</p>

      {loadFailed && <p className="muted">No se pudo cargar el historial de contratos.</p>}

      {contracts !== null && contracts.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Tipo</th>
                <th scope="col">Inicio</th>
                <th scope="col">Fin pactado</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((contract) => (
                <tr key={contract.id}>
                  <td>{CONTRACT_TYPES[contract.contract_type]}</td>
                  <td>{formatDate(contract.start_date)}</td>
                  <td>{contract.end_date === null ? '—' : formatDate(contract.end_date)}</td>
                  <td>
                    {contract.terminated_on === null ? (
                      <span className="badge badge-success">Vigente</span>
                    ) : (
                      `Terminó el ${formatDate(contract.terminated_on)}`
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {canWrite && isAssigning && <AssignContractForm employee={employee} onDone={handleDone} />}

      {canWrite && (
        <div className="form-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setIsAssigning((value) => !value)}
          >
            {isAssigning
              ? 'Cancelar'
              : employee.status === 'INACTIVO'
                ? 'Registrar reingreso'
                : 'Asignar nuevo contrato'}
          </button>
          {employee.status === 'ACTIVO' && (
            <button type="button" className="btn btn-danger" onClick={() => setIsTerminating(true)}>
              Finalizar contrato
            </button>
          )}
        </div>
      )}

      {isTerminating && (
        <TerminateContractModal
          employee={employee}
          onCancel={() => setIsTerminating(false)}
          onDone={handleDone}
        />
      )}
    </div>
  )
}
