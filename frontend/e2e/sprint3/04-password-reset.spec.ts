import { expect, test } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createEmployeeWithAccount, loginStatus } from '../api'
import { fullName } from '../data'
import { readTemporaryPassword, submitLogin } from '../forms'

// Manual step 4. HU-1.5 (#9) an ADMIN resets a forgotten password.
test.use({ storageState: storageStateFor('ADMIN') })

test('ADMIN resets a password: the old one stops working and a change is required', async ({
  page,
  browser,
}) => {
  const { id, person, password } = await createEmployeeWithAccount('EMPLOYEE')

  await page.goto(`/empleados/${id}`)
  await expect(page.getByRole('heading', { level: 1, name: fullName(person) })).toBeVisible()
  await page.getByRole('button', { name: 'Restablecer contraseña' }).click()
  await expect(page.getByText(`¿Restablecer la contraseña de ${fullName(person)}?`)).toBeVisible()
  await page.getByRole('button', { name: 'Sí, restablecer' }).click()

  await expect(page.getByRole('status').filter({ hasText: 'Contraseña restablecida.' })).toBeVisible()
  const temporaryPassword = await readTemporaryPassword(page)

  expect(await loginStatus(person.email, password)).toBe(401)

  // The employee signs in with the new temporary password and must change it.
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } })
  try {
    const employeePage = await context.newPage()
    await employeePage.goto('/login')
    await submitLogin(employeePage, person.email, temporaryPassword)
    await expect(employeePage).toHaveURL(/\/cambiar-contrasena$/)
  } finally {
    await context.close()
  }
})
