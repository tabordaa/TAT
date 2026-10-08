import { api } from './client'
import type { Employee, EmployeeCreatePayload } from '../types/employee'

export async function createEmployee(payload: EmployeeCreatePayload): Promise<Employee> {
  const { data } = await api.post<Employee>('/employees', payload)
  return data
}
