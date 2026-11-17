import { expect, test } from '@playwright/test'
import { createEmployee, loginStatus } from '../api'
import { submitLogin } from '../forms'

// Manual step 9. Login hardening (#79): repeated failures lock the account for a while.
// It uses its own new account: locking a seeded one would break the other specs.
test('wrong passwords in a row show the too-many-attempts message', async ({ page }) => {
  const { person, temporaryPassword } = await createEmployee({ accountRole: 'EMPLOYEE' })
  if (temporaryPassword === null) throw new Error('no account was created')

  await page.goto('/login')
  const alert = page.getByRole('alert')
  let attempts = 0
  while (attempts < 6) {
    attempts += 1
    const answered = page.waitForResponse((response) => response.url().endsWith('/api/auth/login'))
    await submitLogin(page, person.email, `clave-equivocada-${attempts}`)
    if ((await answered).status() === 429) break
    await expect(alert).toContainText('Correo o contraseña incorrectos.')
  }

  await expect(alert).toContainText('Demasiados intentos fallidos.')
  expect(attempts).toBeLessThanOrEqual(6)
  // While locked, even the right password is refused.
  expect(await loginStatus(person.email, temporaryPassword)).toBe(429)
})
