import { readFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'
import { storageStateFor } from '../accounts'

// HU #163: downloadable employment certificate from "Mi perfil".

test.use({ storageState: storageStateFor('EMPLOYEE') })

test.describe('employment certificate', () => {
  test('an active employee downloads their certificate as a PDF', async ({ page }) => {
    await page.goto('/mi-perfil')

    const card = page.getByRole('region', { name: 'CERTIFICADO LABORAL' })
    await expect(card).toBeVisible()
    await expect(card.getByLabel('Incluir salario')).not.toBeChecked()

    const downloadPromise = page.waitForEvent('download')
    await card.getByRole('button', { name: 'Descargar PDF' }).click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/^certificado-laboral-[A-Za-z0-9_-]+\.pdf$/)
    const filePath = await download.path()
    expect(filePath).not.toBeNull()
    if (filePath !== null) {
      const bytes = await readFile(filePath)
      expect(bytes.subarray(0, 4).toString('latin1')).toBe('%PDF')
      expect(bytes.toString('latin1')).not.toContain('devengando')
    }
  })

  test('including the salary adds it to the downloaded PDF', async ({ page }) => {
    await page.goto('/mi-perfil')

    const card = page.getByRole('region', { name: 'CERTIFICADO LABORAL' })
    await card.getByLabel('Incluir salario').check()

    const downloadPromise = page.waitForEvent('download')
    await card.getByRole('button', { name: 'Descargar PDF' }).click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/^certificado-laboral-[A-Za-z0-9_-]+\.pdf$/)
    const filePath = await download.path()
    expect(filePath).not.toBeNull()
    if (filePath !== null) {
      const bytes = await readFile(filePath)
      expect(bytes.subarray(0, 4).toString('latin1')).toBe('%PDF')
      expect(bytes.toString('latin1')).toContain('devengando')
    }
  })
})
