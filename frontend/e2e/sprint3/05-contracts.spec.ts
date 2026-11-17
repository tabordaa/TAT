import { expect, test } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createEmployee, terminateContract } from '../api'
import { businessDate, fullName } from '../data'

// Manual step 5. HU-3.1 (#22) contract assignment, HU-3.2 (#23) expiring contracts.
test.use({ storageState: storageStateFor('HR') })

test('HR assigns a fixed-term contract and it shows up as expiring', async ({ page }) => {
  const { id, person } = await createEmployee()

  await page.goto(`/empleados/${id}`)
  await page.getByRole('button', { name: 'Asignar nuevo contrato' }).click()

  const type = page.getByLabel('Tipo de contrato')
  const end = page.getByLabel('Fecha de finalización')

  // CA03: an open-ended contract has no end date.
  await type.selectOption('INDEFINIDO')
  await expect(end).toBeDisabled()

  // CA02: a fixed-term contract requires one.
  await type.selectOption('FIJO')
  await expect(end).toBeEnabled()
  await page.getByLabel('Fecha de inicio').fill(businessDate())
  await page.getByRole('button', { name: 'Asignar contrato', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('La fecha de finalización es obligatoria')

  await end.fill(businessDate(10))
  await page.getByRole('button', { name: 'Asignar contrato', exact: true }).click()

  // The new contract is the one in force; the previous one stays in the history.
  const history = page.getByRole('table', { name: 'Historial de contratos' })
  await expect(history.getByRole('row').filter({ hasText: 'Término fijo' })).toContainText('Vigente')
  await expect(history.getByRole('row').filter({ hasText: 'Término indefinido' })).toContainText('Terminó el')

  // HU-3.2: ten days left, flagged on the dashboard.
  await page.goto('/dashboard')
  const alerts = page.getByRole('region', { name: 'Contratos por vencer' })
  const row = alerts.getByRole('row').filter({ hasText: fullName(person) })
  await expect(row).toContainText('10 días')
  await expect(row).toContainText('Por vencer')

  // CA03: only ACTIVE employees. After the departure the row disappears.
  await terminateContract(id)
  await page.reload()
  await expect(alerts).toBeVisible()
  await expect(alerts.getByRole('row').filter({ hasText: fullName(person) })).toHaveCount(0)
})
