import { expect, test, type Page } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createEmployee, createEmployeeWithAccount, signIn, terminateContract } from '../api'
import { businessDate } from '../data'

// HU-4.3 (#30): the vacation balance, calculated by the API and always visible.

function balanceCard(page: Page) {
  return page.getByRole('region', { name: 'Saldo de vacaciones' })
}

function balanceValue(page: Page, label: string) {
  return balanceCard(page)
    .getByRole('term')
    .filter({ hasText: new RegExp(`^${label}$`) })
    .locator('xpath=following-sibling::dd[1]')
}

test('an employee with one year of service sees 15 days in their profile', async ({ page }) => {
  const { person, password } = await createEmployeeWithAccount('EMPLOYEE', {
    startDate: businessDate(-365),
  })
  await signIn(page, person.email, password)
  await page.goto('/mi-perfil')

  // CA01 and CA03: 15 days per year, visible in the profile.
  const card = balanceCard(page)
  await expect(card).toContainText('15 días disponibles')
  await expect(balanceValue(page, 'Acumulados')).toHaveText('15')
  await expect(balanceValue(page, 'Usados')).toHaveText('0')
  await expect(balanceValue(page, 'Pendientes de aprobación')).toHaveText('0')
  await expect(balanceValue(page, 'Disponibles para solicitar')).toHaveText('15')
  await expect(card).toContainText('15 días hábiles por año')
})

test('the balance is proportional to the days of the contract in force', async ({ page }) => {
  const { person, password } = await createEmployeeWithAccount('EMPLOYEE', {
    startDate: businessDate(-73),
  })
  await signIn(page, person.email, password)
  await page.goto('/mi-perfil')

  // 15 x 73 / 365 = 3 days exactly.
  await expect(balanceCard(page)).toContainText('3 días disponibles')
})

test.describe('in the employee record', () => {
  test.use({ storageState: storageStateFor('HR') })

  test('HR sees the balance of an active employee', async ({ page }) => {
    const { id } = await createEmployee({ startDate: businessDate(-730) })
    await page.goto(`/empleados/${id}`)

    await expect(balanceCard(page)).toContainText('30 días disponibles')
  })

  test('an inactive employee has no balance', async ({ page }) => {
    const { id } = await createEmployee({ startDate: businessDate(-365) })
    await terminateContract(id)
    await page.goto(`/empleados/${id}`)

    await expect(balanceCard(page)).toContainText('Sin contrato vigente')
  })
})
