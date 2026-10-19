import { api } from './client'
import type {
  Employee,
  EmployeeCreatePayload,
  EmployeeListQuery,
  EmployeeListResponse,
} from '../types/employee'

export async function createEmployee(payload: EmployeeCreatePayload): Promise<Employee> {
  const { data } = await api.post<Employee>('/employees', payload)
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
