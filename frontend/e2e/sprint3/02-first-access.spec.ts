import { expect, test } from '@playwright/test'
import { createEmployee, loginStatus } from '../api'
import { randomPassword } from '../data'
import { submitLogin } from '../forms'

// Manual step 2. HU-1.2 (#5) forced change of the temporary password; HU-1.4 (#8) CA02 one use.
test('a new account must replace its temporary password before anything else', async ({ page }) => {
  const { person, temporaryPassword } = await createEmployee({ accountRole: 'EMPLOYEE' })
  if (temporaryPassword === null) throw new Error('no account was created')

  await page.goto('/login')
  await submitLogin(page, person.email, temporaryPassword)
  await expect(page).toHaveURL(/\/cambiar-contrasena$/)

  // Every route leads back to the change screen.
  await page.goto('/empleados')
  await expect(page).toHaveURL(/\/cambiar-contrasena$/)
  await page.goto('/mi-perfil')
  await expect(page).toHaveURL(/\/cambiar-contrasena$/)

  const current = page.getByLabel('Contraseña temporal', { exact: true })
  const next = page.getByLabel('Nueva contraseña', { exact: true })
  const confirmation = page.getByLabel('Confirma la nueva contraseña', { exact: true })
  const save = page.getByRole('button', { name: 'Guardar contraseña' })

  await current.fill(temporaryPassword)
  await next.fill('corta1')
  await confirmation.fill('corta1')
  await save.click()
  await expect(page.getByText('La nueva contraseña debe tener al menos 8 caracteres.')).toBeVisible()

  await next.fill(temporaryPassword)
  await confirmation.fill(temporaryPassword)
  await save.click()
  await expect(page.getByText('La nueva contraseña debe ser distinta de la actual.')).toBeVisible()

  const password = randomPassword()
  await next.fill(password)
  await confirmation.fill(password)
  await save.click()

  // An EMPLOYEE lands on their own profile and never sees the directory.
  await expect(page).toHaveURL(/\/mi-perfil$/)
  const nav = page.getByRole('navigation', { name: 'Navegación principal' })
  await expect(nav.getByRole('link', { name: 'Mi perfil' })).toBeVisible()
  await expect(nav.getByRole('link', { name: 'Empleados' })).toHaveCount(0)

  // The temporary password was single use; the new one works.
  expect(await loginStatus(person.email, temporaryPassword)).toBe(401)
  expect(await loginStatus(person.email, password)).toBe(200)
})
