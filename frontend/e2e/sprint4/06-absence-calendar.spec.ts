import { expect, test, type Page } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { approveVacation, createPendingVacation } from '../api'
import { addDays, businessDate } from '../data'

// HU-4.4 (#31): a manager plans with the monthly calendar of approved absences.

test.use({ storageState: storageStateFor('MANAGER') })

/** The second Monday of the month two months from now: the range stays inside one month. */
function plannedMonday(): string {
  const today = new Date(`${businessDate()}T12:00:00Z`)
  const target = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() + 2, 8, 12))
  const toMonday = (8 - target.getUTCDay()) % 7
  return addDays(target.toISOString().slice(0, 10), toMonday)
}

function marked(page: Page, name: string) {
  return page
    .getByRole('grid', { name: 'Calendario de ausencias' })
    .getByRole('gridcell', { name: new RegExp(name) })
}

async function openMonth(page: Page, monthsAhead: number): Promise<void> {
  await page.goto('/dashboard')
  await page
    .getByRole('navigation', { name: 'Navegación principal' })
    .getByRole('link', { name: 'Calendario de ausencias' })
    .click()
  await expect(page.getByRole('heading', { name: 'Calendario de ausencias', level: 1 })).toBeVisible()
  for (let step = 0; step < monthsAhead; step += 1) {
    await page.getByRole('button', { name: 'Mes siguiente' }).click()
  }
}

test('approved vacations appear on their business days with the name on hover', async ({
  page,
}) => {
  const monday = plannedMonday()
  // Monday to the next Monday: 6 business days and one weekend in between.
  const approved = await createPendingVacation(365, monday, addDays(monday, 7))
  await approveVacation(approved.requestId)
  const pending = await createPendingVacation(365, monday, addDays(monday, 2))
  const approvedName = `${approved.person.firstNames} ${approved.person.lastNames}`
  const pendingName = `${pending.person.firstNames} ${pending.person.lastNames}`

  await openMonth(page, 2)

  // CA01 and CA02: a grid; only the approved request, only on business days.
  await expect(marked(page, approvedName)).toHaveCount(6)
  await expect(marked(page, pendingName)).toHaveCount(0)
  await expect(page.getByRole('list', { name: /^Ausencias de / })).toContainText(approvedName)

  // CA03: hovering a marked day shows who is away.
  const firstDay = marked(page, approvedName).first()
  await firstDay.hover()
  await expect(firstDay.getByRole('tooltip')).toBeVisible()
  await expect(firstDay.getByRole('tooltip')).toContainText(approvedName)

  // The same with the keyboard: a marked day takes the focus.
  const lastDay = marked(page, approvedName).last()
  await lastDay.focus()
  await expect(lastDay.getByRole('tooltip')).toBeVisible()
})

test('the calendar moves between months', async ({ page }) => {
  await openMonth(page, 0)
  const current = await page.getByRole('heading', { level: 2 }).first().textContent()

  await page.getByRole('button', { name: 'Mes siguiente' }).click()
  await expect(page.getByRole('heading', { level: 2 }).first()).not.toHaveText(current ?? '')
  await page.getByRole('button', { name: 'Mes anterior' }).click()
  await expect(page.getByRole('heading', { level: 2 }).first()).toHaveText(current ?? '')
})

test.describe('as an employee', () => {
  test.use({ storageState: storageStateFor('EMPLOYEE') })

  test('the calendar is not offered', async ({ page }) => {
    await page.goto('/mi-perfil')
    await expect(
      page
        .getByRole('navigation', { name: 'Navegación principal' })
        .getByRole('link', { name: 'Calendario de ausencias' }),
    ).toHaveCount(0)
  })
})
