import { useAuth } from '../auth/useAuth'

export function DashboardPage() {
  const { user } = useAuth()

  return (
    <section>
      <p className="breadcrumb">GESTIÓN HUMANA</p>
      <h1 className="page-title">Hola, {user?.full_name}</h1>
      <p className="page-subtitle">Panel principal de TAT</p>

      <div className="card-grid">
        <article className="card">
          <h2>Empleados</h2>
          <p className="muted">Registro y listado de empleados — en desarrollo.</p>
        </article>
        <article className="card">
          <h2>Métricas</h2>
          <p className="muted">Total, activos e inactivos.</p>
        </article>
      </div>
    </section>
  )
}
