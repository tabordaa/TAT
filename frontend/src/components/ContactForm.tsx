import { useState, type ChangeEvent, type FormEvent } from 'react'
import axios from 'axios'
import { updateMyContact, uploadMyPhoto } from '../api/me'
import type { Employee } from '../types/employee'
import { IconAlert, IconCheck } from './Icons'

const PHONE_PATTERN = /^\+?[0-9 ()-]{7,30}$/ // same rule as the API
const MAX_ADDRESS_LENGTH = 200
const MAX_PHOTO_BYTES = 2 * 1024 * 1024
const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']

function photoErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 413) return 'La foto no puede pesar más de 2 MB.'
    if (error.response?.status === 415) return 'La foto debe ser una imagen JPG, PNG o WEBP.'
    if (error.response?.status === 503) {
      return 'El servicio de fotos no está disponible en este momento.'
    }
  }
  return 'No se pudo subir la foto. Inténtalo de nuevo.'
}

// HU-2.7: only contact fields. Salary, position and the rest are read-only.
export function ContactForm({
  employee,
  onSaved,
}: {
  employee: Employee
  onSaved: (updated: Employee) => void
}) {
  const [phone, setPhone] = useState(employee.phone ?? '')
  const [address, setAddress] = useState(employee.address ?? '')
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setNotice(null)

    const trimmedPhone = phone.trim()
    if (trimmedPhone !== '' && !PHONE_PATTERN.test(trimmedPhone)) {
      setPhoneError('Escribe un teléfono válido: entre 7 y 30 dígitos, espacios o guiones.')
      return
    }
    setPhoneError(null)

    setIsSaving(true)
    try {
      const trimmedAddress = address.trim()
      onSaved(
        await updateMyContact({
          phone: trimmedPhone === '' ? null : trimmedPhone,
          address: trimmedAddress === '' ? null : trimmedAddress,
        }),
      )
      setNotice('Tus datos de contacto se actualizaron.')
    } catch {
      setError('No se pudieron guardar los cambios. Revisa los datos e inténtalo de nuevo.')
    } finally {
      setIsSaving(false)
    }
  }

  async function handlePhoto(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = '' // lets the same file be chosen again after an error
    if (file === undefined) return
    setError(null)
    setNotice(null)

    if (!PHOTO_TYPES.includes(file.type)) {
      setError('La foto debe ser una imagen JPG, PNG o WEBP.')
      return
    }
    if (file.size > MAX_PHOTO_BYTES) {
      setError('La foto no puede pesar más de 2 MB.')
      return
    }

    setIsUploading(true)
    try {
      onSaved(await uploadMyPhoto(file))
      setNotice('Tu foto se actualizó.')
    } catch (err) {
      setError(photoErrorMessage(err))
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <form className="card detail-section" onSubmit={(e) => void handleSubmit(e)} noValidate>
      <p className="section-kicker">ACTUALIZAR MIS DATOS DE CONTACTO</p>

      {error !== null && (
        <div className="alert alert-error" role="alert">
          <IconAlert size={20} />
          <div className="alert-body">
            <span>{error}</span>
          </div>
        </div>
      )}
      {notice !== null && (
        <div className="alert alert-success" role="status">
          <IconCheck size={20} />
          <div className="alert-body">
            <span>{notice}</span>
          </div>
        </div>
      )}

      <div className="form-grid">
        <div className="field">
          <div className="field-label-row">
            <label htmlFor="contact-phone">Teléfono</label>
          </div>
          <input
            id="contact-phone"
            type="tel"
            autoComplete="tel"
            maxLength={30}
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            aria-invalid={phoneError !== null}
            aria-describedby="contact-phone-error"
          />
          {phoneError !== null && (
            <p id="contact-phone-error" className="field-error">
              {phoneError}
            </p>
          )}
        </div>

        <div className="field">
          <div className="field-label-row">
            <label htmlFor="contact-address">Dirección</label>
          </div>
          <input
            id="contact-address"
            type="text"
            autoComplete="street-address"
            maxLength={MAX_ADDRESS_LENGTH}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
        </div>

        <div className="field">
          <div className="field-label-row">
            <label htmlFor="contact-photo">Foto de perfil</label>
          </div>
          <input
            id="contact-photo"
            type="file"
            accept={PHOTO_TYPES.join(',')}
            disabled={isUploading}
            onChange={(e) => void handlePhoto(e)}
          />
          <p className="field-help">{isUploading ? 'Subiendo foto…' : 'JPG, PNG o WEBP, hasta 2 MB.'}</p>
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={isSaving}>
          {isSaving ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </div>
    </form>
  )
}
