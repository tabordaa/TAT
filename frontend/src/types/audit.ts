// Mirrors backend/app/schemas/audit.py (the API contract).

export interface FieldChange {
  old: string | null
  new: string | null
}

export interface AuditLogItem {
  id: string
  actor_email: string
  action: string
  entity_type: string
  entity_id: string
  changes: Record<string, FieldChange>
  ip: string
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogItem[]
  total: number
  page: number
  size: number
}
