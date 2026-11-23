import { useState } from 'react'
import axios from 'axios'
import { downloadEmploymentCertificate } from '../api/me'
import { IconAlert, IconDownload } from './Icons'

function certificateErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.status === 409) {
    return 'Solo un empleado activo con contrato vigente puede descargar el certificado.'
  }
  return 'No se pudo generar el certificado. Inténtalo de nuevo.'
}

// HU #163: self-service PDF certificate from the employee's own profile.
export function CertificateCard({ documentNumber }: { documentNumber: string }) {
  const [withSalary, setWithSalary] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDownload() {
    setIsDownloading(true)
    setError(null)
    try {
      const blob = await downloadEmploymentCertificate(withSalary)
      const safeDoc = documentNumber.replace(/[^A-Za-z0-9_-]/g, '')
      const filename =
        safeDoc !== '' ? `certificado-laboral-${safeDoc}.pdf` : 'certificado-laboral.pdf'
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      // Release on the next tick: revoking synchronously can cancel the download.
      setTimeout(() => URL.revokeObjectURL(url), 0)
    } catch (err) {
      setError(certificateErrorMessage(err))
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <section className="card detail-section" aria-labelledby="certificate-title">
      <h2 id="certificate-title" className="section-kicker">
        CERTIFICADO LABORAL
      </h2>
      <p className="muted">
        Descarga un certificado con tu cargo, tipo de contrato y fecha de ingreso para bancos,
        arriendos o trámites.
      </p>

      {error !== null && (
        <div className="alert alert-error" role="alert">
          <IconAlert size={20} />
          <div className="alert-body">
            <span>{error}</span>
          </div>
        </div>
      )}

      <div className="certificate-actions">
        <label className="certificate-checkbox" htmlFor="certificate-with-salary">
          <input
            id="certificate-with-salary"
            type="checkbox"
            checked={withSalary}
            disabled={isDownloading}
            onChange={(event) => setWithSalary(event.target.checked)}
          />
          <span>Incluir salario</span>
        </label>
        <button
          type="button"
          className="btn btn-primary"
          disabled={isDownloading}
          onClick={() => void handleDownload()}
        >
          <IconDownload />
          {isDownloading ? 'Generando…' : 'Descargar PDF'}
        </button>
      </div>
    </section>
  )
}
