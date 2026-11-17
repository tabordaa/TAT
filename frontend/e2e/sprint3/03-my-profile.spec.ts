import { expect, test } from '@playwright/test'
import { createEmployeeWithAccount, signIn } from '../api'
import { fullName } from '../data'

// Manual step 3. HU-2.6 (#18) my profile, HU-2.7 (#19) contact details and photo.

// The smallest valid PNG (1x1 pixel): the API recognizes images by their bytes.
const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
)

test.describe('my profile', () => {
  test('an employee sees their record and edits only the contact fields', async ({ page }) => {
    const { person, password } = await createEmployeeWithAccount('EMPLOYEE')
    await signIn(page, person.email, password)

    await page.goto('/')
    await expect(page).toHaveURL(/\/mi-perfil$/)
    await expect(page.getByRole('heading', { level: 1, name: fullName(person) })).toBeVisible()
    await expect(page.getByText(person.position).first()).toBeVisible()

    // Salary and the rest are read-only: the form has no field for them.
    await expect(page.getByLabel('Salario mensual (COP)')).toHaveCount(0)
    await expect(page.getByLabel('Cargo')).toHaveCount(0)

    await page.getByLabel('Teléfono').fill('+57 310 555 2847')
    await page.getByLabel('Dirección').fill('Calle 49 # 50-21, Medellín')
    await page.getByRole('button', { name: 'Guardar cambios' }).click()
    await expect(page.getByRole('status')).toContainText('Tus datos de contacto se actualizaron.')

    await page.reload()
    await expect(page.getByLabel('Teléfono')).toHaveValue('+57 310 555 2847')
    await expect(page.getByLabel('Dirección')).toHaveValue('Calle 49 # 50-21, Medellín')
  })

  test('a file that is not an image is rejected, in the browser and by the API', async ({ page }) => {
    const { person, password } = await createEmployeeWithAccount('EMPLOYEE')
    await signIn(page, person.email, password)
    await page.goto('/mi-perfil')

    await page.getByLabel('Foto de perfil').setInputFiles({
      name: 'hoja-de-vida.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.7 not an image'),
    })
    await expect(page.getByRole('alert')).toContainText('La foto debe ser una imagen JPG, PNG o WEBP.')

    // The browser check is only UX: the server decides by the bytes, not the declared type.
    const response = await page.request.put('/api/me/employee/photo', {
      multipart: {
        photo: { name: 'foto.png', mimeType: 'image/png', buffer: Buffer.from('%PDF-1.7 not an image') },
      },
    })
    expect(response.status()).toBe(415)
  })

  test('uploads a profile photo to the real bucket', async ({ page }) => {
    test.skip(process.env.E2E_STORAGE !== '1', 'needs Supabase Storage: run with E2E_STORAGE=1')
    const { person, password } = await createEmployeeWithAccount('EMPLOYEE')
    await signIn(page, person.email, password)
    await page.goto('/mi-perfil')

    await page.getByLabel('Foto de perfil').setInputFiles({
      name: 'foto.png',
      mimeType: 'image/png',
      buffer: PNG_1X1,
    })
    await expect(page.getByRole('status')).toContainText('Tu foto se actualizó.')

    const photo = await page.request.get('/api/me/employee/photo')
    expect(photo.status()).toBe(200)
    expect(photo.headers()['content-type']).toBe('image/png')
  })
})
