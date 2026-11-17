import { expect, test, type Page } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createPendingVacation } from '../api'
import { addDays, nextMonday } from '../data'

// HU-4.2 (#28): HR approves or rejects pending requests from the inbox.
// The approval also proves HU-4.3 CA02 in the browser: only APPROVED days are used.

test.use({ storageState: storageStateFor('HR') })

function inboxRow(page: Page, employeeName: string) {
  return page
    .getByRole('table', { name: 'Solicitudes pendientes' })
    .getByRole('row')
    .filter({ hasText: employeeName })
}

function balanceValue(page: Page, label: string) {
  return page
    .getByRole('region', { name: 'Saldo de vacaciones' })
    .getByRole('term')
    .filter({ hasText: new RegExp(`^${label}$`) })
    .locator('xpath=following-sibling::dd[1]')
}

async function openInbox(page: Page): Promise<void> {
  await page.goto('/dashboard')
  await page
    .getByRole('navigation', { name: 'Navegación principal' })
    .getByRole('link', { name: 'Solicitudes de vacaciones' })
    .click()
  await expect(page.getByRole('heading', { name: 'Solicitudes de vacaciones' })).toBeVisible()
}

test('HR approves a request and the days are used', async ({ page }) => {
  const monday = nextMonday(3)
  const { person, id } = await createPendingVacation(365, monday, addDays(monday, 4))
  const name = `${person.firstNames} ${person.lastNames}`
  await openInbox(page)

  // CA01: the pending request is in the table, with the employee and the days.
  const row = inboxRow(page, name)
  await expect(row).toContainText('5')
  await row.getByRole('button', { name: `Aprobar solicitud de ${name}` }).click()

  // CA02: approved and gone from the pending list.
  await expect(page.getByRole('status').filter({ hasText: `Solicitud de ${name} aprobada.` })).toBeVisible()
  await expect(inboxRow(page, name)).toHaveCount(0)

  // HU-4.3 CA02: the approved days are subtracted from the balance.
  await page.goto(`/empleados/${id}`)
  await expect(balanceValue(page, 'Usados')).toHaveText('5')
  await expect(balanceValue(page, 'Pendientes de aprobación')).toHaveText('0')
  await expect(page.getByRole('region', { name: 'Saldo de vacaciones' })).toContainText(
    '10 días disponibles',
  )
})

test('HR rejects a request with a mandatory reason and no days are used', async ({ page }) => {
  const monday = nextMonday(4)
  const { person, id } = await createPendingVacation(365, monday, addDays(monday, 2))
  const name = `${person.firstNames} ${person.lastNames}`
  await openInbox(page)

  await inboxRow(page, name).getByRole('button', { name: `Rechazar solicitud de ${name}` }).click()
  const dialog = page.getByRole('dialog', { name: `Rechazar vacaciones de ${name}` })
  await expect(dialog).toBeVisible()

  // CA03: the reason is mandatory.
  await dialog.getByRole('button', { name: 'Rechazar solicitud' }).click()
  await expect(dialog.getByText('Escribe el motivo del rechazo')).toBeVisible()

  await dialog.getByLabel('Motivo del rechazo').fill('Cierre contable de fin de mes')
  await dialog.getByRole('button', { name: 'Rechazar solicitud' }).click()

  await expect(dialog).toBeHidden()
  await expect(page.getByRole('status').filter({ hasText: `Solicitud de ${name} rechazada.` })).toBeVisible()
  await expect(inboxRow(page, name)).toHaveCount(0)

  // HU-4.3 CA02: a rejected request uses no days.
  await page.goto(`/empleados/${id}`)
  await expect(balanceValue(page, 'Usados')).toHaveText('0')
  await expect(balanceValue(page, 'Pendientes de aprobación')).toHaveText('0')
  await expect(page.getByRole('region', { name: 'Saldo de vacaciones' })).toContainText(
    '15 días disponibles',
  )
})

test.describe('as a manager', () => {
  test.use({ storageState: storageStateFor('MANAGER') })

  test('the inbox is not offered', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(
      page
        .getByRole('navigation', { name: 'Navegación principal' })
        .getByRole('link', { name: 'Solicitudes de vacaciones' }),
    ).toHaveCount(0)
  })
})
