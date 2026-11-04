import { useState, type ReactNode } from 'react'
import { CONTRACT_TYPES, DOCUMENT_TYPES, type Employee } from '../types/employee'

const dateFormatter = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long', timeZone: 'UTC' })
const salaryFormatter = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 2,
})

/** "2026-01-15" -> "15 de enero de 2026". Parsed as UTC so the day never shifts with the time zone. */
function formatDate(isoDate: string): string {
  return dateFormatter.format(new Date(`${isoDate}T00:00:00Z`))
}

/** First letter of the first name plus first letter of the first last name. */
function getInitials(employee: Employee): string {
  const first = employee.first_names.trim().charAt(0)
  const last = employee.last_names.trim().charAt(0)
  return `${first}${last}`.toUpperCase()
}

function DetailItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="detail-item">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

/** The private photo, served by the API, or the initials if there is none or it fails to load. */
function Avatar({ employee, photoUrl }: { employee: Employee; photoUrl: string }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null)

  if (!employee.has_photo || failedUrl === photoUrl) {
    return (
      <span className="avatar avatar-lg" aria-hidden="true">
        {getInitials(employee)}
      </span>
    )
  }
  return (
    <img
      className="avatar avatar-lg avatar-photo"
      src={photoUrl}
      alt=""
      onError={() => setFailedUrl(photoUrl)}
    />
  )
}

export function EmployeeRecordHeader({
  employee,
  photoUrl,
}: {
  employee: Employee
  photoUrl: string
}) {
  return (
    <div className="detail-header">
      <Avatar employee={employee} photoUrl={photoUrl} />
      <div className="detail-header-text">
        <div className="detail-title-row">
          <h1 className="page-title">
            {employee.first_names} {employee.last_names}
          </h1>
          <span
            className={employee.status === 'ACTIVO' ? 'badge badge-success' : 'badge badge-muted'}
          >
            {employee.status === 'ACTIVO' ? 'Activo' : 'Inactivo'}
          </span>
        </div>
        <p className="page-subtitle">
          {employee.position} · {employee.area}
        </p>
      </div>
    </div>
  )
}

export function PersonalDataSection({ employee }: { employee: Employee }) {
  return (
    <div className="card detail-section">
      <p className="section-kicker">DATOS PERSONALES</p>
      <dl className="detail-grid">
        <DetailItem label="Nombres">{employee.first_names}</DetailItem>
        <DetailItem label="Apellidos">{employee.last_names}</DetailItem>
        <DetailItem label="Tipo de documento">{DOCUMENT_TYPES[employee.document_type]}</DetailItem>
        <DetailItem label="Número de documento">{employee.document_number}</DetailItem>
        <DetailItem label="Correo electrónico">{employee.email}</DetailItem>
        <DetailItem label="Teléfono">{employee.phone ?? 'No registrado'}</DetailItem>
        <DetailItem label="Dirección">{employee.address ?? 'No registrada'}</DetailItem>
      </dl>
    </div>
  )
}

export function EmploymentDataSection({ employee }: { employee: Employee }) {
  return (
    <div className="card detail-section">
      <p className="section-kicker">DATOS LABORALES</p>
      <dl className="detail-grid">
        <DetailItem label="Cargo">{employee.position}</DetailItem>
        <DetailItem label="Área">{employee.area}</DetailItem>
        <DetailItem label="Salario">{salaryFormatter.format(Number(employee.salary))}</DetailItem>
        <DetailItem label="Tipo de contrato">{CONTRACT_TYPES[employee.contract_type]}</DetailItem>
        <DetailItem label="Fecha de inicio">{formatDate(employee.start_date)}</DetailItem>
        <DetailItem label="Fecha de finalización">
          {employee.end_date === null ? 'Sin fecha de fin' : formatDate(employee.end_date)}
        </DetailItem>
      </dl>
    </div>
  )
}
