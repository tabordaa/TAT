import { expect, test } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createEmployeeWithAccount, loginStatus, terminateContract } from '../api'
import { businessDate } from '../data'
import { readTemporaryPassword, recordTitle } from '../forms'

// Manual step 7. HU-3.1 (#22) rehire: the record comes back, the access does not until a reset.
test.use({ storageState: storageStateFor('ADMIN') })

test('a rehire reactivates the employee but not the account, until an ADMIN resets it', async ({
  page,
}) => {
  const { id, person, password } = await createEmployeeWithAccount('EMPLOYEE')
  await terminateContract(id)

  await page.goto(`/empleados/${id}`)
  await page.getByRole('button', { name: 'Registrar reingreso' }).click()
  await expect(page.getByText('Su acceso al sistema no se reactiva')).toBeVisible()
  await page.getByLabel('Tipo de contrato').selectOption('INDEFINIDO')
  await page.getByLabel('Fecha de inicio').fill(businessDate())
  await page.getByRole('button', { name: 'Registrar reingreso' }).click()

  await expect(recordTitle(page)).toContainText('Activo')
  await expect(page.getByRole('button', { name: 'Finalizar contrato' })).toBeVisible()
  const history = page.getByRole('table', { name: 'Historial de contratos' })
  await expect(history.getByRole('row')).toHaveCount(3) // header + old contract + new one
  await expect(history.getByRole('row').filter({ hasText: 'Vigente' })).toHaveCount(1)

  // Still no access with the old password.
  expect(await loginStatus(person.email, password)).toBe(401)

  // The ADMIN gives it back with a reset.
  await page.getByRole('button', { name: 'Restablecer contraseña' }).click()
  await page.getByRole('button', { name: 'Sí, restablecer' }).click()
  const temporaryPassword = await readTemporaryPassword(page)
  expect(await loginStatus(person.email, temporaryPassword)).toBe(200)
})
