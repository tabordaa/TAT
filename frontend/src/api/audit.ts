import { api } from './client'
import type { AuditLogListResponse } from '../types/audit'

/** GET /audit: the trail of critical changes, newest first (ADMIN only). */
export async function listAuditLogs(
  page: number,
  size: number,
  signal?: AbortSignal,
): Promise<AuditLogListResponse> {
  const { data } = await api.get<AuditLogListResponse>('/audit', {
    params: { page, size },
    signal,
  })
  return data
}
