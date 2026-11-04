import { api } from './client'
import type { Contract, ContractAlert, ContractAssignPayload, Employee } from '../types/employee'

function contractsUrl(employeeId: string): string {
  return `/employees/${encodeURIComponent(employeeId)}/contracts`
}

export async function listContracts(employeeId: string, signal?: AbortSignal): Promise<Contract[]> {
  const { data } = await api.get<Contract[]>(contractsUrl(employeeId), { signal })
  return data
}

/** POST /employees/{id}/contracts. For an inactive employee it is also the rehire. */
export async function assignContract(
  employeeId: string,
  payload: ContractAssignPayload,
): Promise<Employee> {
  const { data } = await api.post<Employee>(contractsUrl(employeeId), payload)
  return data
}

/** POST /employees/{id}/contracts/terminate. Also disables the login account. */
export async function terminateContract(employeeId: string, endDate: string): Promise<Employee> {
  const { data } = await api.post<Employee>(`${contractsUrl(employeeId)}/terminate`, {
    end_date: endDate,
  })
  return data
}

/** GET /employees/contract-alerts: contracts ending in under 30 days, soonest first. */
export async function getContractAlerts(signal?: AbortSignal): Promise<ContractAlert[]> {
  const { data } = await api.get<ContractAlert[]>('/employees/contract-alerts', { signal })
  return data
}
