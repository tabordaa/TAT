import { api } from './client'
import type {
  AccountCreated,
  Employee,
  EmployeeCreated,
  EmployeeCreatePayload,
  EmployeeDetail,
  EmployeeListQuery,
  EmployeeListResponse,
  EmployeeOverview,
  EmployeeStats,
  EmploymentUpdatePayload,
  SalaryChange,
} from '../types/employee'

/** GET /employees/{id}. Rejects with an axios 404 error when the employee does not exist. */
export async function getEmployee(id: string, signal?: AbortSignal): Promise<EmployeeDetail> {
  const { data } = await api.get<EmployeeDetail>(`/employees/${encodeURIComponent(id)}`, { signal })
  return data
}

/** POST /employees/{id}/account/reset-password (ADMIN). The password is returned only here. */
export async function resetAccountPassword(employeeId: string): Promise<AccountCreated> {
  const { data } = await api.post<AccountCreated>(
    `/employees/${encodeURIComponent(employeeId)}/account/reset-password`,
  )
  return data
}

/** PATCH /employees/{id}/employment (ADMIN and HR): position, area and salary. */
export async function updateEmployment(
  employeeId: string,
  payload: EmploymentUpdatePayload,
): Promise<Employee> {
  const { data } = await api.patch<Employee>(
    `/employees/${encodeURIComponent(employeeId)}/employment`,
    payload,
  )
  return data
}

/** GET /employees/{id}/salary-history: every salary change, newest first. */
export async function getSalaryHistory(
  employeeId: string,
  signal?: AbortSignal,
): Promise<SalaryChange[]> {
  const { data } = await api.get<SalaryChange[]>(
    `/employees/${encodeURIComponent(employeeId)}/salary-history`,
    { signal },
  )
  return data
}

export async function createEmployee(payload: EmployeeCreatePayload): Promise<EmployeeCreated> {
  const { data } = await api.post<EmployeeCreated>('/employees', payload)
  return data
}

/** GET /employees. The signal lets the caller cancel a request that became stale. */
export async function listEmployees(
  query: EmployeeListQuery,
  signal?: AbortSignal,
): Promise<EmployeeListResponse> {
  const { data } = await api.get<EmployeeListResponse>('/employees', {
    // Empty filters are simply not sent: the API then applies no filter.
    params: {
      page: query.page,
      size: query.size,
      ...(query.q !== '' && { q: query.q }),
      ...(query.status !== '' && { status: query.status }),
    },
    signal,
  })
  return data
}

/** GET /employees/stats: headline numbers for the dashboard. */
export async function getEmployeeStats(signal?: AbortSignal): Promise<EmployeeStats> {
  const { data } = await api.get<EmployeeStats>('/employees/stats', { signal })
  return data
}

/** GET /employees/overview: distributions and recent movements for the dashboard charts. */
export async function getEmployeeOverview(signal?: AbortSignal): Promise<EmployeeOverview> {
  const { data } = await api.get<EmployeeOverview>('/employees/overview', { signal })
  return data
}
