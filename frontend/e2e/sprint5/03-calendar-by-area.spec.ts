import { expect, test, type Page } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { approveVacation, createPendingVacation } from '../api'
import { addDays, businessDate, fullName, nextMonday } from '../data'

// HU-4.8 (#162): a manager filters the absence calendar by area.

test.use({ storageState: storageStateFor('MANAGER') })

const AREA = 'Logística'
const OTHER_AREA = 'Contabilidad'

function monthsBetween(from: string, to: string): number {
  return (
    (Number(to.slice(0, 4)) - Number(from.slice(0, 4))) * 12 +
    Number(to.slice(5, 7)) -
    Number(from.slice(5, 7))
  )
}

function calendar(page: Page) {
  return page.getByRole('grid', { name: 'Calendario de ausencias' })
}

async function approvedIn(area: string, monday: string) {
  const created = await createPendingVacation(365, monday, addDays(monday, 2), { area })
  await approveVacation(created.requestId)
  return fullName(created.person)
}

test('the calendar shows only the chosen area and counts who is away on a day', async ({
  page,
}) => {
  const monday = nextMonday(9)
  const first = await approvedIn(AREA, monday)
  const second = await approvedIn(AREA, monday)
  const elsewhere = await approvedIn(OTHER_AREA, monday)

  await page.goto('/vacaciones/calendario')
  await expect(page.getByRole('heading', { name: 'Calendario de ausencias', level: 1 })).toBeVisible()
  for (let step = 0; step < monthsBetween(businessDate(), monday); step += 1) {
    await page.getByRole('button', { name: 'Mes siguiente' }).click()
  }

  // Without a filter, everybody.
  await expect(calendar(page).getByRole('gridcell', { name: new RegExp(elsewhere) })).toHaveCount(3)

  // CA01: the server filters by area.
  await page.getByLabel('Área').selectOption(AREA)
  await expect(calendar(page).getByRole('gridcell', { name: new RegExp(elsewhere) })).toHaveCount(0)
  await expect(calendar(page).getByRole('gridcell', { name: new RegExp(first) })).toHaveCount(3)
  await expect(calendar(page).getByRole('gridcell', { name: new RegExp(second) })).toHaveCount(3)

  // CA02: choosing a day says how many people of the area are away. Other runs
  // may have left more people of this area on the same day: count the cell itself.
  const day = calendar(page).locator(`[data-date="${monday}"]`)
  await day.click()
  const names = (await day.getByRole('tooltip').textContent()) ?? ''
  const count = names.split(', ').length
  expect(count).toBeGreaterThanOrEqual(2)
  await expect(page.getByRole('status').filter({ hasText: `del área ${AREA}` })).toHaveText(
    new RegExp(`^${count} personas del área ${AREA} ausentes el `),
  )
})
