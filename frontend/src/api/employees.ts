import { api } from './client'
import type {
  Employee,
  EmployeeCreated,
  EmployeeCreatePayload,
  EmployeeListQuery,
  EmployeeListResponse,
  EmployeeOverview,
  EmployeeStats,
} from '../types/employee'

/** GET /employees/{id}. Rejects with an axios 404 error when the employee does not exist. */
export async function getEmployee(id: string, signal?: AbortSignal): Promise<Employee> {
  const { data } = await api.get<Employee>(`/employees/${encodeURIComponent(id)}`, { signal })
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
