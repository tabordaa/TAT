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
    // An empty status is simply not sent: the API then returns everyone.
    params: {
      page: query.page,
      size: query.size,
      ...(query.status !== '' && { status: query.status }),
    },
    signal,
  })
  return data
}
