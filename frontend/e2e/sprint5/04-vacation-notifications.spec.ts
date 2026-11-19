import { expect, test, type Page } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { approveVacation, createPendingVacation, signIn } from '../api'
import { addDays, nextMonday } from '../data'

// HU-4.7 (#161): counters in the sidebar and the news of a decided request.

function sidebar(page: Page) {
  return page.getByRole('navigation', { name: 'Navegación principal' })
}

/** The number in "N pendientes" next to "Solicitudes de vacaciones" (0 when hidden). */
async function pendingBadge(page: Page): Promise<number> {
  const link = sidebar(page).getByRole('link', { name: /^Solicitudes de vacaciones/ })
  await expect(link).toBeVisible()
  const text = (await link.textContent()) ?? ''
  const match = /(\d+) pendientes?/.exec(text)
  return match === null ? 0 : Number(match[1])
}

test.describe('as HR', () => {
  test.use({ storageState: storageStateFor('HR') })

  test('the pending counter grows with a new request and drops after a decision', async ({
    page,
  }) => {
    await page.goto('/dashboard')
    const before = await pendingBadge(page)

    const monday = nextMonday(10)
    const { person } = await createPendingVacation(365, monday, addDays(monday, 1))
    await page.reload()
    // CA01
    await expect.poll(() => pendingBadge(page)).toBe(before + 1)

    await sidebar(page).getByRole('link', { name: /^Solicitudes de vacaciones/ }).click()
    const name = `${person.firstNames} ${person.lastNames}`
    await page.getByRole('button', { name: `Aprobar solicitud de ${name}` }).click()
    await expect(page.getByRole('status').filter({ hasText: `Solicitud de ${name} aprobada.` })).toBeVisible()
    // The badge follows the decision without a reload.
    await expect.poll(() => pendingBadge(page)).toBe(before)
  })
})

test('an employee sees the decision once, marked as new', async ({ page }) => {
  const monday = nextMonday(11)
  const { person, password, requestId } = await createPendingVacation(
    365,
    monday,
    addDays(monday, 2),
  )
  await approveVacation(requestId)
  await signIn(page, person.email, password)

  // CA02: a mark in the sidebar while there is news.
  await page.goto('/mi-perfil')
  const myVacations = sidebar(page).getByRole('link', { name: /^Mis vacaciones/ })
  await expect(myVacations).toContainText('1 novedad')

  await myVacations.click()
  await expect(
    page.getByRole('status').filter({ hasText: 'se decidió desde tu última visita' }),
  ).toBeVisible()
  const row = page.getByRole('table', { name: 'Mis solicitudes de vacaciones' }).getByRole('row').nth(1)
  await expect(row).toContainText('Aprobada')
  await expect(row).toContainText('Nueva')
  await expect(myVacations).not.toContainText('novedad')

  // Seen: the next visit has no news.
  await page.goto('/mi-perfil')
  await sidebar(page).getByRole('link', { name: /^Mis vacaciones/ }).click()
  await expect(page.getByRole('heading', { name: 'Mis vacaciones' })).toBeVisible()
  await expect(page.getByText('desde tu última visita')).toHaveCount(0)
  await expect(row).not.toContainText('Nueva')
})
