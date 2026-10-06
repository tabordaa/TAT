import { Link } from 'react-router'
import { IconUserPlus, IconUsers } from '../components/Icons'

// HU-2.2 (listado y búsqueda) is the next increment; this is the entry point.
export function EmployeesPage() {
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

      <div className="card empty-state">
        <IconUsers size={32} />
        <h2>Aún no hay empleados registrados</h2>
        <p className="muted">El listado con búsqueda llega en la HU-2.2.</p>
      </div>
    </section>
  )
}
