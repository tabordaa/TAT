import { expect, test } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { loginStatus } from '../api'
import { fullName, randomPerson } from '../data'
import { readTemporaryPassword } from '../forms'

// Manual step 1. HU-1.4 (#8) account created with the employee, HU-5.1 (#34) audit trail.
test.use({ storageState: storageStateFor('ADMIN') })

test('ADMIN registers an employee with an account, and the audit log records it', async ({ page }) => {
  const person = randomPerson()
  await page.goto('/empleados/nuevo')

  await page.getByLabel('Nombres').fill(person.firstNames)
  await page.getByLabel('Apellidos').fill(person.lastNames)
  await page.getByLabel('Tipo de documento').selectOption('CC')
  await page.getByLabel('Número de documento').fill(person.documentNumber)
  await page.getByLabel('Correo electrónico').fill(person.email)
  await page.getByLabel('Teléfono').fill(person.phone)
  await page.getByLabel('Cargo').fill(person.position)
  await page.getByLabel('Área / Departamento').fill(person.area)
  await page.getByLabel('Salario mensual (COP)').fill(person.salary)
  await page.getByLabel('Tipo de contrato').selectOption('INDEFINIDO')
  await page.getByLabel('Fecha de inicio').fill('2025-02-03')
  await page.getByLabel('Rol de la cuenta').selectOption('EMPLOYEE')
  await page.getByRole('button', { name: 'Guardar empleado' }).click()

  await expect(page.getByRole('status')).toContainText('Empleado registrado y cuenta de acceso creada.')
  await expect(page.getByText(`${fullName(person)} ya puede ingresar`)).toBeVisible()
  const temporaryPassword = await readTemporaryPassword(page)

  // HU-1.4: the account works with the temporary password (it must be changed on first use).
  expect(await loginStatus(person.email, temporaryPassword)).toBe(200)

  // HU-5.1: both changes are in the trail, newest first, with the actor.
  await page.goto('/auditoria')
  const rows = page.getByRole('row').filter({ hasText: 'laura.restrepo@tat.example.com' })
  await expect(rows.filter({ hasText: 'Cuenta creada' }).filter({ hasText: person.email })).toHaveCount(1)
  await expect(rows.filter({ hasText: 'Empleado registrado' }).first()).toBeVisible()
  // The temporary password never reaches the audit log.
  await expect(page.getByText(temporaryPassword)).toHaveCount(0)
})
