import { Link, useLocation } from 'react-router'
import { IconCheck, IconUserPlus, IconUsers } from '../components/Icons'

/** Reads the name sent by RegisterEmployeePage after a successful save. */
function getCreatedName(state: unknown): string | null {
  if (typeof state === 'object' && state !== null && 'createdName' in state) {
    const { createdName } = state
    return typeof createdName === 'string' ? createdName : null
  }
  return null
}

// HU-2.2 (listado y búsqueda) is the next increment; this is the entry point.
export function EmployeesPage() {
  const createdName = getCreatedName(useLocation().state)

  return (
    <section>
      <div className="page-header">
        <div>
          <p className="breadcrumb">GESTIÓN HUMANA · Directorio central</p>
          <h1 className="page-title">Empleados</h1>
          <p className="page-subtitle">Gestión de contratos y cargos de la organización</p>
        </div>
        <Link to="/empleados/nuevo" className="btn btn-primary">
          <IconUserPlus /> Registrar empleado
        </Link>
      </div>

      {createdName !== null && (
        <div className="alert alert-success" role="status">
          <IconCheck size={20} />
          <div className="alert-body">
            <strong>Empleado registrado.</strong>
            <span>{createdName} quedó registrado con estado ACTIVO.</span>
          </div>
        </div>
      )}

      <div className="card empty-state">
        <IconUsers size={32} />
        <h2>El listado de empleados llega en la HU-2.2</h2>
        <p className="muted">Por ahora puedes registrar nuevos empleados.</p>
      </div>
    </section>
  )
}
