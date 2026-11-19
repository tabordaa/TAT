import { expect, test, type Page } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createEmployeeWithAccount, signIn } from '../api'
import { addDays, businessDate, nextWeekWithHoliday } from '../data'

// HU-4.6 (#160): Colombian holidays are not vacation days.

const longDate = new Intl.DateTimeFormat('es-CO', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

function monthsBetween(from: string, to: string): number {
  return (
    (Number(to.slice(0, 4)) - Number(from.slice(0, 4))) * 12 +
    Number(to.slice(5, 7)) -
    Number(from.slice(5, 7))
  )
}

async function openMyVacations(page: Page): Promise<void> {
  const { person, password } = await createEmployeeWithAccount('EMPLOYEE', {
    startDate: businessDate(-365),
  })
  await signIn(page, person.email, password)
  await page.goto('/mis-vacaciones')
  await expect(page.getByRole('heading', { name: 'Mis vacaciones' })).toBeVisible()
}

test('a week with a holiday counts one business day less', async ({ page }) => {
  const { monday, holiday } = nextWeekWithHoliday()
  await openMyVacations(page)

  await page.getByLabel('Fecha de inicio').fill(monday)
  await page.getByLabel('Fecha de fin').fill(addDays(monday, 4))

  // CA02: the form counts like the server, and says which holiday it left out.
  const count = page.locator('#vacation-business-days')
  await expect(count).toContainText('Días hábiles solicitados: 4')
  await expect(count).toContainText('Festivos en el rango')
  await page.getByRole('button', { name: 'Enviar solicitud' }).click()

  await expect(
    page.getByRole('status').filter({ hasText: 'Solicitud enviada por 4 días hábiles.' }),
  ).toBeVisible()
  const row = page.getByRole('table', { name: 'Mis solicitudes de vacaciones' }).getByRole('row').nth(1)
  await expect(row.getByRole('cell').nth(2)).toHaveText('4')
  expect(holiday >= monday).toBe(true)
})

test.describe('the calendar', () => {
  test.use({ storageState: storageStateFor('MANAGER') })

  test('marks the holidays with their name', async ({ page }) => {
    const { holiday } = nextWeekWithHoliday()
    await page.goto('/vacaciones/calendario')
    await expect(page.getByRole('heading', { name: 'Calendario de ausencias', level: 1 })).toBeVisible()
    for (let step = 0; step < monthsBetween(businessDate(), holiday); step += 1) {
      await page.getByRole('button', { name: 'Mes siguiente' }).click()
    }

    // CA03
    const label = longDate.format(new Date(`${holiday}T00:00:00Z`))
    const cell = page
      .getByRole('grid', { name: 'Calendario de ausencias' })
      .getByRole('gridcell', { name: new RegExp(`^${label}: festivo, `) })
    await expect(cell).toHaveCount(1)
  })
})

test.describe('as an admin', () => {
  test.use({ storageState: storageStateFor('ADMIN') })

  // Far from any real holiday: harmless even if a failed run leaves it behind.
  const DECREED = '2099-09-17'

  test('adds a decreed holiday and removes it', async ({ page }) => {
    await page.goto('/dashboard')
    await page
      .getByRole('navigation', { name: 'Navegación principal' })
      .getByRole('link', { name: 'Festivos' })
      .click()
    await expect(page.getByRole('heading', { name: 'Festivos', level: 1 })).toBeVisible()
    // CA01: the seeded holidays of this year are listed.
    const year = businessDate().slice(0, 4)
    await expect(page.getByRole('table', { name: `Festivos de ${year}` })).toContainText('Navidad')

    await page.getByLabel('Fecha').fill(DECREED)
    await page.getByLabel('Nombre').fill('Día cívico de prueba')
    await page.getByRole('button', { name: 'Agregar festivo' }).click()

    await expect(page.getByRole('status').filter({ hasText: 'Festivo agregado' })).toBeVisible()
    const table = page.getByRole('table', { name: 'Festivos de 2099' })
    await expect(table).toContainText('Día cívico de prueba')

    await table.getByRole('button', { name: 'Eliminar festivo Día cívico de prueba' }).click()
    await table.getByRole('button', { name: 'Sí, eliminar' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Festivo eliminado' })).toBeVisible()
    await expect(page.getByText('No hay festivos registrados para 2099.')).toBeVisible()
  })

  test.describe('as HR', () => {
    test.use({ storageState: storageStateFor('HR') })

    test('the holidays page is not offered', async ({ page }) => {
      await page.goto('/dashboard')
      await expect(
        page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', {
          name: 'Festivos',
        }),
      ).toHaveCount(0)
    })
  })
})
