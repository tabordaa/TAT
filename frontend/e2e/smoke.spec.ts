import { expect, test } from '@playwright/test'
import { ACCOUNTS, ROLES, e2ePassword, storageStateFor } from './accounts'
import { saveSession } from './session'

// Smoke test of the E2E setup: every seeded role reaches its home screen with
// the saved session, and the login form itself works (HU-1.1, HU-1.3).

for (const role of ROLES) {
  test.describe(`${role} session`, () => {
    test.use({ storageState: storageStateFor(role) })

    test(`lands on its home screen`, async ({ page }) => {
      const account = ACCOUNTS[role]
      await page.goto('/')

      await expect(page).toHaveURL(role === 'EMPLOYEE' ? /\/mi-perfil$/ : /\/dashboard$/)
      // The header: the profile page repeats the name in its title.
      const header = page.getByRole('banner')
      await expect(header.getByText(account.fullName, { exact: true })).toBeVisible()
      await expect(header.getByText(account.roleLabel, { exact: true })).toBeVisible()

      const nav = page.getByRole('navigation', { name: 'Navegación principal' })
      const employees = nav.getByRole('link', { name: 'Empleados' })
      if (role === 'EMPLOYEE') {
        await expect(employees).toHaveCount(0)
      } else {
        await expect(employees).toBeVisible()
      }
      await expect(nav.getByRole('link', { name: 'Auditoría' })).toHaveCount(role === 'ADMIN' ? 1 : 0)
    })
  })
}

test.describe('without a session', () => {
  test('a protected page sends the visitor to the login', async ({ page }) => {
    await page.goto('/empleados')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('unknown credentials get the generic error', async ({ page }) => {
    await page.goto('/login')
    // An address no account uses: a wrong password for a real account would
    // count toward that account's lockout.
    await page.getByLabel('Correo electrónico').fill('nadie.registrado@tat.example.com')
    await page.getByLabel('Contraseña', { exact: true }).fill('una-clave-cualquiera')
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()

    await expect(page.getByRole('alert')).toContainText('Correo o contraseña incorrectos.')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('signs in through the form and signs out', async ({ page }) => {
    const account = ACCOUNTS.MANAGER
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(account.email)
    await page.getByLabel('Contraseña', { exact: true }).fill(e2ePassword())
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()

    await expect(page).toHaveURL(/\/dashboard$/)
    await page.getByRole('button', { name: 'Cerrar sesión' }).click()
    await expect(page).toHaveURL(/\/login$/)

    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login$/)

    // Logout revoked every MANAGER session, the saved one too: restore it.
    await saveSession('MANAGER')
  })
})
