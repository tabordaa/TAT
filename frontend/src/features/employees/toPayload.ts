import type { EmployeeCreatePayload, EmployeeFormValues } from '../../types/employee'

/** '' → null for optional fields, so the API receives "no value" explicitly. */
function optional(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

/**
 * Maps the form (camelCase, UI-oriented) to the API contract (snake_case).
 * Call only after validateEmployee() returned no errors.
 */
export function toEmployeePayload(values: EmployeeFormValues): EmployeeCreatePayload {
  if (values.documentType === '' || values.contractType === '') {
    throw new Error('toEmployeePayload called with an invalid form')
  }
  return {
    first_names: values.firstNames.trim(),
    last_names: values.lastNames.trim(),
    document_type: values.documentType,
    document_number: values.documentNumber.trim(),
    email: values.email.trim(),
    phone: optional(values.phone),
    position: values.position.trim(),
    area: values.area.trim(),
    salary: values.salary.trim(),
    contract_type: values.contractType,
    start_date: values.startDate,
    end_date: values.endDate === '' ? null : values.endDate,
  }
}
