import { useEffect, useState } from 'react'
import axios from 'axios'
import { getMyEmployee } from '../api/me'
import {
  EmployeeRecordHeader,
  EmploymentDataSection,
  PersonalDataSection,
} from '../components/EmployeeRecord'
import { IconAlert, IconUser } from '../components/Icons'
import type { Employee } from '../types/employee'

type Load =
  | { phase: 'loading' }
  | { phase: 'not-linked' }
  | { phase: 'error' }
  | { phase: 'ready'; employee: Employee }

// HU-2.6: the signed-in person's own record. No id in the URL: the API takes it
// from the session, so there is nothing to tamper with.
export function MyProfilePage() {
  const [load, setLoad] = useState<Load>({ phase: 'loading' })
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoad({ phase: 'loading' })

    getMyEmployee(controller.signal)
      .then((employee) => setLoad({ phase: 'ready', employee }))
      .catch((error: unknown) => {
        if (axios.isCancel(error)) return
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          setLoad({ phase: 'not-linked' })
          return
        }
        setLoad({ phase: 'error' })
      })

    return () => controller.abort()
  }, [reloadCount])

  return (
    <section>
      {load.phase === 'loading' && (
        <p className="table-status muted" role="status">
          Cargando tu perfil…
        </p>
      )}

      {load.phase === 'not-linked' && (
        <div className="card empty-state">
          <IconUser size={32} />
          <h2>Tu cuenta no tiene un expediente</h2>
          <p className="muted">Pide a Recursos Humanos que la vincule con tu registro de empleado.</p>
        </div>
      )}

      {load.phase === 'error' && (
        <div className="alert alert-error" role="alert">
          <IconAlert size={20} />
          <div className="alert-body">
            <strong>No se pudo cargar tu perfil.</strong>
            <span>Revisa tu conexión e inténtalo de nuevo.</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setReloadCount((count) => count + 1)}
          >
            Reintentar
          </button>
        </div>
      )}

      {load.phase === 'ready' && (
        <>
          <EmployeeRecordHeader employee={load.employee} />
          <div className="detail-sections">
            <PersonalDataSection employee={load.employee} />
            <EmploymentDataSection employee={load.employee} />
          </div>
        </>
      )}
    </section>
  )
}
