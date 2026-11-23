import { expect, test } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createEmployee } from '../api'
import { fullName } from '../data'

// Manual step 8. Role permissions (3 nov): a MANAGER reads the directory, never writes.
test.use({ storageState: storageStateFor('MANAGER') })

test('a MANAGER sees the directory, the dashboard and records, without any write action', async ({
  page,
}) => {
  const { id, person } = await createEmployee()

  await page.goto('/dashboard')
  await expect(page.getByRole('region', { name: 'Contratos por vencer' })).toBeVisible()

  await page.goto('/empleados')
  await expect(page.getByRole('heading', { level: 1, name: 'Empleados' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Registrar empleado' })).toHaveCount(0)

  await page.goto(`/empleados/${id}`)
  await expect(page.getByRole('heading', { level: 1, name: fullName(person) })).toBeVisible()
  // Exact: while loading, the skeleton keeps a hidden "Cargando contratos…" for screen readers.
  await expect(page.getByText('CONTRATOS', { exact: true })).toBeVisible()
  for (const action of ['Asignar nuevo contrato', 'Finalizar contrato', 'Restablecer contraseña']) {
    await expect(page.getByRole('button', { name: action })).toHaveCount(0)
  }

  const nav = page.getByRole('navigation', { name: 'Navegación principal' })
  await expect(nav.getByRole('link', { name: 'Auditoría' })).toHaveCount(0)
  await page.goto('/auditoria')
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.goto('/empleados/nuevo')
  await expect(page).toHaveURL(/\/dashboard$/)

  // Hiding buttons is only UX: the API refuses the writes too.
  const terminate = await page.request.post(`/api/employees/${id}/contracts/terminate`, {
    data: { end_date: '2026-01-01' },
  })
  expect(terminate.status()).toBe(403)
  const audit = await page.request.get('/api/audit')
  expect(audit.status()).toBe(403)
})
