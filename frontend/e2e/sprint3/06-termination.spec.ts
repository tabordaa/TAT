import { expect, test } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createEmployeeWithAccount, loginStatus, signIn } from '../api'
import { businessDate, fullName } from '../data'
import { recordTitle, submitLogin } from '../forms'

// Manual step 6. HU-3.3 (#24) termination in two steps; the account and its sessions end.
test.use({ storageState: storageStateFor('HR') })

test('HR terminates a contract: the person can no longer sign in and their open session ends', async ({
  page,
  browser,
}) => {
  const { id, person, password } = await createEmployeeWithAccount('EMPLOYEE')

  // The employee has the app open in another browser.
  const employeeContext = await browser.newContext({ storageState: { cookies: [], origins: [] } })
  const employeePage = await employeeContext.newPage()
  await signIn(employeePage, person.email, password)
  await employeePage.goto('/mi-perfil')
  await expect(employeePage.getByRole('heading', { level: 1, name: fullName(person) })).toBeVisible()

  await page.goto(`/empleados/${id}`)
  await page.getByRole('button', { name: 'Finalizar contrato' }).click()
  const dialog = page.getByRole('dialog', { name: `Finalizar contrato de ${fullName(person)}` })
  await expect(dialog).toBeVisible()

  // Step 1: the date, which cannot be missing or in the future.
  await dialog.getByRole('button', { name: 'Continuar' }).click()
  await expect(dialog.getByRole('alert')).toContainText('Selecciona la fecha de salida.')
  await dialog.getByLabel('Fecha de salida').fill(businessDate(1))
  await dialog.getByRole('button', { name: 'Continuar' }).click()
  await expect(dialog.getByRole('alert')).toContainText('no puede ser futura')
  await dialog.getByLabel('Fecha de salida').fill(businessDate())
  await dialog.getByRole('button', { name: 'Continuar' }).click()

  // Step 2: an explicit confirmation that says what will happen.
  await expect(dialog).toContainText('quedará inactivo')
  await dialog.getByRole('button', { name: 'Sí, finalizar contrato' }).click()
  await expect(dialog).toHaveCount(0)

  await expect(recordTitle(page)).toContainText('Inactivo')
  await expect(page.getByRole('button', { name: 'Registrar reingreso' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Finalizar contrato' })).toHaveCount(0)

  // The open session died: the next request answers 401 and the app goes to the login.
  await employeePage.reload()
  await expect(employeePage).toHaveURL(/\/login$/)
  await submitLogin(employeePage, person.email, password)
  await expect(employeePage.getByRole('alert')).toContainText('Correo o contraseña incorrectos.')
  await employeeContext.close()

  expect(await loginStatus(person.email, password)).toBe(401)
})
