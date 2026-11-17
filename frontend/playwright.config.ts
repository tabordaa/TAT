import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'
import { BASE_URL } from './e2e/session'

const here = path.dirname(fileURLToPath(import.meta.url))

// Local runs read E2E_PASSWORD from this git-ignored file; CI sets it directly.
const localEnv = path.join(here, 'e2e', '.env.e2e')
if (existsSync(localEnv)) {
  process.loadEnvFile(localEnv)
}

const isCI = process.env.CI === 'true'
const backendDir = path.join(here, '..', 'backend')
// The local venv on Windows; plain `python` on the CI runner.
const python =
  process.env.E2E_PYTHON ??
  (process.platform === 'win32' ? path.join(backendDir, '.venv', 'Scripts', 'python.exe') : 'python')

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  // One database shared by every test: run them one at a time.
  workers: 1,
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: !isCI,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --strictPort',
      cwd: here,
      url: BASE_URL,
      reuseExistingServer: !isCI,
      timeout: 120_000,
    },
  ],
})
