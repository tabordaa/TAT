import { expect, test, type APIRequestContext } from '@playwright/test'
import { ACCOUNTS, storageStateFor } from '../accounts'
import { apiAs, createEmployee } from '../api'
import { fullName } from '../data'

// HU-2.5 (#16): the salary history in the employee record, for managers and admins.

async function raise(hr: APIRequestContext, employeeId: string, salary: string): Promise<void> {
  const response = await hr.patch(`/api/employees/${employeeId}/employment`, { data: { salary } })
  expect(response.status(), 'PATCH employment').toBe(200)
}

test.describe('as MANAGER', () => {
  test.use({ storageState: storageStateFor('MANAGER') })

  test('sees every salary change, newest first, with old and new salary, date and who', async ({
    page,
  }) => {
    const { id, person } = await createEmployee()
    const hr = await apiAs('HR')
    try {
      await raise(hr, id, '3950000')
      await raise(hr, id, '4300000')
    } finally {
      await hr.dispose()
    }

    await page.goto(`/empleados/${id}`)
    await expect(page.getByRole('heading', { level: 1, name: fullName(person) })).toBeVisible()

    // CA01: a "Historial salarial" section in the record.
    const history = page.getByRole('region', { name: 'Historial salarial' })
    await expect(history).toBeVisible()

    // CA02: old salary, new salary and date of each change (plus who made it).
    const columns = history.getByRole('columnheader')
    await expect(columns).toHaveText(['Fecha del cambio', 'Salario anterior', 'Salario nuevo', 'Responsable'])
    const rows = history.getByRole('row').filter({ hasNot: page.getByRole('columnheader') })
    await expect(rows).toHaveCount(2)

    const newest = rows.nth(0).getByRole('cell')
    await expect(newest.nth(1)).toContainText('3.950.000')
    await expect(newest.nth(2)).toContainText('4.300.000')
    await expect(newest.nth(3)).toHaveText(ACCOUNTS.HR.fullName)
    await expect(newest.nth(0)).toContainText(/\d{4}/) // a real date, formatted for Colombia

    const oldest = rows.nth(1).getByRole('cell')
    await expect(oldest.nth(1)).toContainText(Number(person.salary).toLocaleString('es-CO'))
    await expect(oldest.nth(2)).toContainText('3.950.000')
  })

  test('a record without changes says so', async ({ page }) => {
    const { id } = await createEmployee()
    await page.goto(`/empleados/${id}`)

    const history = page.getByRole('region', { name: 'Historial salarial' })
    await expect(history).toContainText('Aún no hay cambios de salario registrados.')
  })
})

test.describe('as HR', () => {
  test.use({ storageState: storageStateFor('HR') })

  test('a raise made from the record appears in the history at once', async ({ page }) => {
    const { id } = await createEmployee()
    await page.goto(`/empleados/${id}`)
    const history = page.getByRole('region', { name: 'Historial salarial' })
    await expect(history).toContainText('Aún no hay cambios')

    await page.getByRole('button', { name: 'Editar datos laborales' }).click()
    await page.getByLabel('Salario mensual (COP)').fill('5100000')
    await page.getByRole('button', { name: 'Guardar datos laborales' }).click()

    await expect(history.getByRole('row').filter({ hasText: '5.100.000' })).toHaveCount(1)
  })
})

test('an EMPLOYEE cannot read anyone’s salary history through the API', async () => {
  const { id } = await createEmployee()
  const employee = await apiAs('EMPLOYEE')
  try {
    const response = await employee.get(`/api/employees/${id}/salary-history`)
    expect(response.status()).toBe(403)
  } finally {
    await employee.dispose()
  }
})
