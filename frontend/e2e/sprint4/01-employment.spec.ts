import { expect, test, type Page } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { apiAs, createEmployee, terminateContract } from '../api'
import { fullName } from '../data'

// HU-2.4 (#15): ADMIN and HR edit position, area and salary; a salary change is logged.

function detailValue(page: Page, label: string) {
  return page.getByRole('term').filter({ hasText: new RegExp(`^${label}$`) }).locator('xpath=following-sibling::dd[1]')
}

test.describe('as HR', () => {
  test.use({ storageState: storageStateFor('HR') })

  test('promotes and raises an employee, and the audit log records the salary change', async ({
    page,
    browser,
  }) => {
    const { id, person } = await createEmployee()
    await page.goto(`/empleados/${id}`)
    await expect(page.getByRole('heading', { level: 1, name: fullName(person) })).toBeVisible()

    await page.getByRole('button', { name: 'Editar datos laborales' }).click()
    const form = page.getByRole('form', { name: 'EDITAR DATOS LABORALES' })
    const position = form.getByLabel('Cargo')
    const area = form.getByLabel('Área / Departamento')
    const salary = form.getByLabel('Salario mensual (COP)')
    const save = form.getByRole('button', { name: 'Guardar datos laborales' })

    // The form starts from the current values.
    await expect(position).toHaveValue(person.position)
    await expect(salary).toHaveValue(new RegExp(`^${person.salary}(\\.00)?$`))

    // Client validation (UX; the API validates again).
    await salary.fill('')
    await save.click()
    await expect(form.getByText('Este campo es obligatorio.')).toBeVisible()
    await salary.fill('4.500.000')
    await save.click()
    await expect(form.getByText('Usa solo números, con máximo 2 decimales')).toBeVisible()

    // CA01: position, area and salary.
    await position.fill('Coordinadora de talento humano')
    await area.fill('Talento Humano')
    await salary.fill('4750000')
    await save.click()

    await expect(form).toHaveCount(0)
    await expect(detailValue(page, 'Cargo')).toHaveText('Coordinadora de talento humano')
    await expect(detailValue(page, 'Área')).toHaveText('Talento Humano')
    await expect(detailValue(page, 'Salario')).toContainText('4.750.000')

    // CA02: the change is recorded automatically, with the old and new salary.
    const adminContext = await browser.newContext({ storageState: storageStateFor('ADMIN') })
    try {
      const admin = await adminContext.newPage()
      await admin.goto('/auditoria')
      const row = admin
        .getByRole('row')
        .filter({ hasText: 'Datos laborales actualizados' })
        .filter({ hasText: '4750000' })
        .first()
      await expect(row).toContainText('andres.cardona@tat.example.com')
      await expect(row).toContainText(`Salario: ${Number(person.salary).toFixed(2)} → 4750000.00`)
    } finally {
      await adminContext.close()
    }
  })

  test('saving the same values tells there is nothing to change', async ({ page }) => {
    const { id } = await createEmployee()
    await page.goto(`/empleados/${id}`)
    await page.getByRole('button', { name: 'Editar datos laborales' }).click()
    const form = page.getByRole('form', { name: 'EDITAR DATOS LABORALES' })
    await form.getByRole('button', { name: 'Guardar datos laborales' }).click()

    await expect(form.getByRole('status')).toContainText('No hay cambios para guardar.')
  })

  test('an inactive employee has no edit button', async ({ page }) => {
    const { id } = await createEmployee()
    await terminateContract(id)
    await page.goto(`/empleados/${id}`)

    await expect(page.getByRole('button', { name: 'Registrar reingreso' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Editar datos laborales' })).toHaveCount(0)
  })
})

test.describe('as MANAGER', () => {
  test.use({ storageState: storageStateFor('MANAGER') })

  test('reads the job data but cannot edit it, in the UI or through the API', async ({ page }) => {
    const { id, person } = await createEmployee()
    await page.goto(`/empleados/${id}`)

    await expect(detailValue(page, 'Cargo')).toHaveText(person.position)
    await expect(page.getByRole('button', { name: 'Editar datos laborales' })).toHaveCount(0)

    const manager = await apiAs('MANAGER')
    try {
      const response = await manager.patch(`/api/employees/${id}/employment`, {
        data: { salary: '99000000' },
      })
      expect(response.status()).toBe(403)
    } finally {
      await manager.dispose()
    }
  })
})
