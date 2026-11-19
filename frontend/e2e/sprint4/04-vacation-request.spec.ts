import { expect, test, type Page } from '@playwright/test'
import { createEmployeeWithAccount, signIn } from '../api'
import { COLOMBIAN_HOLIDAYS, addDays, businessDate, nextMonday } from '../data'

// HU-4.1 (#27): an employee requests vacations from "Mis vacaciones".

async function openMyVacations(page: Page, days: number): Promise<void> {
  const { person, password } = await createEmployeeWithAccount('EMPLOYEE', {
    startDate: businessDate(-days),
  })
  await signIn(page, person.email, password)
  await page.goto('/mi-perfil')
  await page.getByRole('navigation', { name: 'Navegación principal' })
    .getByRole('link', { name: 'Mis vacaciones' })
    .click()
  await expect(page.getByRole('heading', { name: 'Mis vacaciones' })).toBeVisible()
}

async function chooseDates(page: Page, start: string, end: string): Promise<void> {
  // CA01: native date pickers (a calendar in every browser).
  await page.getByLabel('Fecha de inicio').fill(start)
  await page.getByLabel('Fecha de fin').fill(end)
}

function balanceValue(page: Page, label: string) {
  return page
    .getByRole('region', { name: 'Saldo de vacaciones' })
    .getByRole('term')
    .filter({ hasText: new RegExp(`^${label}$`) })
    .locator('xpath=following-sibling::dd[1]')
}

test('an employee requests a week and it stays pending', async ({ page }) => {
  await openMyVacations(page, 365)
  const monday = nextMonday()
  await chooseDates(page, monday, addDays(monday, 4))

  // CA02: the business days are counted before sending.
  await expect(page.locator('#vacation-business-days')).toContainText('Días hábiles solicitados: 5')
  await page.getByRole('button', { name: 'Enviar solicitud' }).click()

  await expect(
    page.getByRole('status').filter({ hasText: 'Queda pendiente de aprobación.' }),
  ).toBeVisible()
  // CA04: PENDIENTE in my list.
  const row = page.getByRole('table', { name: 'Mis solicitudes de vacaciones' }).getByRole('row').nth(1)
  await expect(row).toContainText('Pendiente')
  await expect(row.getByRole('cell').nth(2)).toHaveText('5')
  // The pending days are held, but not subtracted from the available ones.
  await expect(balanceValue(page, 'Pendientes de aprobación')).toHaveText('5')
  await expect(balanceValue(page, 'Disponibles para solicitar')).toHaveText('10')
  await expect(balanceValue(page, 'Acumulados')).toHaveText('15')
})

test('weekends inside the range are not counted', async ({ page }) => {
  await openMyVacations(page, 365)
  // A Friday whose next Monday is not a holiday either (HU-4.6).
  let week = 1
  while (COLOMBIAN_HOLIDAYS.has(addDays(nextMonday(week), 7))) week += 1
  const friday = addDays(nextMonday(week), 4)
  await chooseDates(page, friday, addDays(friday, 3))

  await expect(page.locator('#vacation-business-days')).toContainText('Días hábiles solicitados: 2')
})

test('a request above the balance cannot be sent', async ({ page }) => {
  await openMyVacations(page, 73) // 3 days earned
  const monday = nextMonday()
  await chooseDates(page, monday, addDays(monday, 4))
  await page.getByRole('button', { name: 'Enviar solicitud' }).click()

  // CA03
  await expect(page.getByText('Superas tus días disponibles para solicitar')).toBeVisible()
  await expect(page.getByText('Aún no has solicitado vacaciones.')).toBeVisible()
})

test('a range overlapping a pending request is rejected by the server', async ({ page }) => {
  await openMyVacations(page, 365)
  const monday = nextMonday(2)
  await chooseDates(page, monday, addDays(monday, 1))
  await page.getByRole('button', { name: 'Enviar solicitud' }).click()
  await expect(
    page.getByRole('status').filter({ hasText: 'Queda pendiente de aprobación.' }),
  ).toBeVisible()

  await chooseDates(page, addDays(monday, 1), addDays(monday, 3))
  await page.getByRole('button', { name: 'Enviar solicitud' }).click()

  await expect(page.getByText('Se cruza con otra solicitud pendiente o aprobada.')).toBeVisible()
})

test('a range of only weekend days cannot be sent', async ({ page }) => {
  await openMyVacations(page, 365)
  const saturday = addDays(nextMonday(), 5)
  await chooseDates(page, saturday, addDays(saturday, 1))

  await expect(page.locator('#vacation-business-days')).toContainText('Días hábiles solicitados: 0')
  await page.getByRole('button', { name: 'Enviar solicitud' }).click()
  await expect(page.getByText('El rango no tiene días hábiles')).toBeVisible()
})
