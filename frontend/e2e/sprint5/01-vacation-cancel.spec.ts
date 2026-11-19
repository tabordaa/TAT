import { expect, test, type Page } from '@playwright/test'
import { approveVacation, createPendingVacation, signIn } from '../api'
import { addDays, nextMonday } from '../data'

// HU-4.5 (#159): an employee cancels their own request from "Mis vacaciones".

function myRequests(page: Page) {
  return page.getByRole('table', { name: 'Mis solicitudes de vacaciones' })
}

function balanceValue(page: Page, label: string) {
  return page
    .getByRole('region', { name: 'Saldo de vacaciones' })
    .getByRole('term')
    .filter({ hasText: new RegExp(`^${label}$`) })
    .locator('xpath=following-sibling::dd[1]')
}

async function openMyVacations(page: Page, email: string, password: string): Promise<void> {
  await signIn(page, email, password)
  await page.goto('/mis-vacaciones')
  await expect(page.getByRole('heading', { name: 'Mis vacaciones' })).toBeVisible()
}

test('a pending request is cancelled after confirming and the days come back', async ({ page }) => {
  const monday = nextMonday(5)
  const { person, password } = await createPendingVacation(365, monday, addDays(monday, 4))
  await openMyVacations(page, person.email, password)
  await expect(balanceValue(page, 'Disponibles para solicitar')).toHaveText('10')

  // CA01: the button is there for a pending request; it asks before acting.
  const row = myRequests(page).getByRole('row').nth(1)
  await row.getByRole('button', { name: /^Cancelar solicitud del/ }).click()
  const confirm = row.getByRole('group', { name: 'Confirmar cancelación' })
  await expect(confirm).toContainText('¿Cancelar esta solicitud?')
  await confirm.getByRole('button', { name: 'Sí, cancelar' }).click()

  // CA02: CANCELADA and the days are requestable again at once.
  await expect(page.getByRole('status').filter({ hasText: 'cancelada' })).toBeVisible()
  await expect(row).toContainText('Cancelada')
  await expect(row).toContainText('Cancelada por el empleado')
  await expect(row.getByRole('button', { name: /^Cancelar solicitud del/ })).toHaveCount(0)
  await expect(balanceValue(page, 'Disponibles para solicitar')).toHaveText('15')
})

test('an approved request that has not started can be cancelled too', async ({ page }) => {
  const monday = nextMonday(6)
  const { person, password, requestId } = await createPendingVacation(
    365,
    monday,
    addDays(monday, 1),
  )
  await approveVacation(requestId)
  await openMyVacations(page, person.email, password)
  await expect(balanceValue(page, 'Usados')).toHaveText('2')

  const row = myRequests(page).getByRole('row').nth(1)
  await expect(row).toContainText('Aprobada')
  await row.getByRole('button', { name: /^Cancelar solicitud del/ }).click()
  await row.getByRole('button', { name: 'Sí, cancelar' }).click()

  await expect(row).toContainText('Cancelada')
  await expect(balanceValue(page, 'Usados')).toHaveText('0')
})

test('saying no keeps the request', async ({ page }) => {
  const monday = nextMonday(7)
  const { person, password } = await createPendingVacation(365, monday, addDays(monday, 2))
  await openMyVacations(page, person.email, password)

  const row = myRequests(page).getByRole('row').nth(1)
  await row.getByRole('button', { name: /^Cancelar solicitud del/ }).click()
  await row.getByRole('button', { name: 'No', exact: true }).click()

  await expect(row).toContainText('Pendiente')
  await expect(row.getByRole('button', { name: /^Cancelar solicitud del/ })).toBeVisible()
})
