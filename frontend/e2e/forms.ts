import { expect, type Locator, type Page } from '@playwright/test'

/** Fills and submits the login form (the page must be on /login). */
export async function submitLogin(page: Page, email: string, password: string): Promise<void> {
  await page.getByLabel('Correo electrónico').fill(email)
  await page.getByLabel('Contraseña', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Iniciar sesión' }).click()
}

/** Reads the temporary password shown once by TemporaryPasswordPanel. */
export async function readTemporaryPassword(page: Page): Promise<string> {
  const value = page
    .getByRole('term')
    .filter({ hasText: 'Contraseña temporal' })
    .locator('xpath=following-sibling::dd[1]')
  await expect(value).toBeVisible()
  const password = (await value.innerText()).trim()
  expect(password.length).toBeGreaterThanOrEqual(12)
  return password
}

/** The title row of an employee record: the name (h1) and the status badge next to it. */
export function recordTitle(page: Page): Locator {
  return page.getByRole('heading', { level: 1 }).locator('xpath=..')
}
