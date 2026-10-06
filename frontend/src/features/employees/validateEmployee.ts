import {
  CONTRACTS_WITH_END_DATE,
  type EmployeeFormErrors,
  type EmployeeFormValues,
} from '../../types/employee'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const DOCUMENT_PATTERN = /^[A-Za-z0-9-]{4,20}$/

/**
 * Client-side validation = fast feedback for the user.
 * The backend MUST validate again (the client can always be bypassed),
 * including the unique document rule, which only the database can guarantee.
 */
export function validateEmployee(values: EmployeeFormValues): EmployeeFormErrors {
  const errors: EmployeeFormErrors = {}
  const required = 'Este campo es obligatorio.'

  if (values.firstNames.trim() === '') errors.firstNames = required
  if (values.lastNames.trim() === '') errors.lastNames = required
  if (values.documentType === '') errors.documentType = required

  if (values.documentNumber.trim() === '') {
    errors.documentNumber = required
  } else if (!DOCUMENT_PATTERN.test(values.documentNumber.trim())) {
    errors.documentNumber = 'Usa entre 4 y 20 letras, números o guiones.'
  }

  if (values.email.trim() !== '' && !EMAIL_PATTERN.test(values.email.trim())) {
    errors.email = 'Ingresa un correo válido.'
  }

  if (values.position.trim() === '') errors.position = required
  if (values.contractType === '') errors.contractType = required
  if (values.startDate === '') errors.startDate = required

  const needsEndDate =
    values.contractType !== '' && CONTRACTS_WITH_END_DATE.includes(values.contractType)
  if (needsEndDate && values.endDate === '') {
    errors.endDate = 'Obligatoria para este tipo de contrato.'
  }
  // ISO dates (yyyy-mm-dd) compare correctly as strings.
  if (values.endDate !== '' && values.startDate !== '' && values.endDate < values.startDate) {
    errors.endDate = 'No puede ser anterior a la fecha de inicio.'
  }

  return errors
}
