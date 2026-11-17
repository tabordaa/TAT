import { readFile } from 'node:fs/promises'
import { expect, test, type Page } from '@playwright/test'
import { storageStateFor } from '../accounts'
import { createEmployee, terminateContract } from '../api'

// HU-5.2 (#36): "Exportar" downloads the directory with the filters on screen.

/** Applies the search and status filters, then downloads and parses the CSV. */
async function exportWith(page: Page, search: string, status: string): Promise<string[][]> {
  await page.goto('/empleados')
  await page.getByLabel('Buscar').fill(search)
  await page.getByLabel('Estado').selectOption(status)
  // The search waits for a pause in typing: export only once the table shows
  // the filtered result (a header row and the one match).
  await expect(page.getByRole('table').getByRole('row')).toHaveCount(2)
  await expect(page.getByRole('table')).toContainText(search)

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar' }).click() // CA01
  const file = await download
  expect(file.suggestedFilename()).toMatch(/^empleados-\d{4}-\d{2}-\d{2}\.csv$/)

  const text = await readFile(await file.path(), 'utf-8')
  expect(text.charCodeAt(0)).toBe(0xfeff) // BOM: Excel reads tildes and the ñ
  return text
    .slice(1)
    .trim()
    .split('\r\n')
    .map((line) => line.split(';'))
}

test.describe('as HR', () => {
  test.use({ storageState: storageStateFor('HR') })

  test('the file holds only the employees the filters show, with salary', async ({ page }) => {
    const active = await createEmployee()
    const left = await createEmployee()
    await terminateContract(left.id)
    const rows = await exportWith(page, active.person.documentNumber, 'ACTIVO')

    // CA02: the search and the status filter are applied to the file.
    expect(rows[0]).toContain('Salario')
    expect(rows).toHaveLength(2)
    expect(rows[1]?.[3]).toBe(active.person.documentNumber)
    expect(rows.flat()).not.toContain(left.person.documentNumber)
  })

  test('an inactive filter exports the departure', async ({ page }) => {
    const left = await createEmployee()
    await terminateContract(left.id)

    const rows = await exportWith(page, left.person.documentNumber, 'INACTIVO')

    expect(rows).toHaveLength(2)
    expect(rows[1]).toContain('Inactivo')
  })
})

test.describe('as a manager', () => {
  test.use({ storageState: storageStateFor('MANAGER') })

  test('the file has no salary column', async ({ page }) => {
    const active = await createEmployee()

    const rows = await exportWith(page, active.person.documentNumber, 'ACTIVO')

    expect(rows[0]).not.toContain('Salario')
    expect(rows[1]?.[0]).toBe(active.person.firstNames)
  })
})
