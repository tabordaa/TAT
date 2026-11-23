import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { getMyVacationBalance, getVacationBalance } from '../api/vacations'
import type { VacationBalance } from '../types/vacation'
import { SkeletonCard } from './Skeleton'

// "15.00" -> "15", "1.23" -> "1,23": the balance can have a fraction of a day.
const daysFormatter = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 })

function days(value: string | number): string {
  return daysFormatter.format(Number(value))
}

const dateFormatter = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long', timeZone: 'UTC' })

type Load = { phase: 'loading' } | { phase: 'error' } | { phase: 'ready'; balance: VacationBalance }

interface VacationBalanceCardProps {
  /** Whose balance: an employee's record, or null for the signed-in person (Mi perfil). */
  employeeId: string | null
  /** Changes when the balance may have changed (a new request, a decision). */
  version?: string | number
  /** Hands the loaded balance to the page (Mis vacaciones checks the form against it). */
  onLoaded?: (balance: VacationBalance) => void
}

// HU-4.3 CA03: the available days, always visible in the profile. The numbers
// come from the API, which calculates them on every read.
export function VacationBalanceCard({ employeeId, version = 0, onLoaded }: VacationBalanceCardProps) {
  const [state, setState] = useState<Load>({ phase: 'loading' })
  // The latest callback without making it an effect dependency (the parent
  // recreates it on every render, which would refetch in a loop).
  const onLoadedRef = useRef(onLoaded)
  useEffect(() => {
    onLoadedRef.current = onLoaded
  })

  useEffect(() => {
    const controller = new AbortController()
    setState({ phase: 'loading' })
    const request =
      employeeId === null
        ? getMyVacationBalance(controller.signal)
        : getVacationBalance(employeeId, controller.signal)
    request
      .then((balance) => {
        setState({ phase: 'ready', balance })
        onLoadedRef.current?.(balance)
      })
      .catch((error: unknown) => {
        if (!axios.isCancel(error)) setState({ phase: 'error' })
      })
    return () => controller.abort()
  }, [employeeId, version])

  return (
    <section className="card detail-section" aria-labelledby="vacation-balance-title">
      <h2 id="vacation-balance-title" className="section-kicker">
        SALDO DE VACACIONES
      </h2>

      {state.phase === 'loading' && (
        <SkeletonCard bare variant="balance" label="Calculando saldo…" />
      )}
      {state.phase === 'error' && <p className="muted">No se pudo calcular el saldo de vacaciones.</p>}

      {state.phase === 'ready' && state.balance.contract_start === null && (
        <p className="muted">Sin contrato vigente: no acumula días de vacaciones.</p>
      )}

      {state.phase === 'ready' && state.balance.contract_start !== null && (
        <>
          <p className="balance-headline">
            <strong className="balance-number">{days(state.balance.available_days)}</strong>{' '}
            días disponibles
          </p>
          <dl className="detail-grid">
            <div className="detail-item">
              <dt>Acumulados</dt>
              <dd>{days(state.balance.accrued_days)}</dd>
            </div>
            <div className="detail-item">
              <dt>Usados</dt>
              <dd>{days(state.balance.used_days)}</dd>
            </div>
            <div className="detail-item">
              <dt>Pendientes de aprobación</dt>
              <dd>{days(state.balance.pending_days)}</dd>
            </div>
            <div className="detail-item">
              <dt>Disponibles para solicitar</dt>
              <dd>{days(state.balance.requestable_days)}</dd>
            </div>
          </dl>
          <p className="field-help">
            {state.balance.days_per_year} días hábiles por año, proporcionales al contrato vigente
            desde el {dateFormatter.format(new Date(`${state.balance.contract_start}T00:00:00Z`))}.
          </p>
        </>
      )}
    </section>
  )
}
