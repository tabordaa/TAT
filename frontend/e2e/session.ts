import { request } from '@playwright/test'
import { ACCOUNTS, e2ePassword, storageStateFor, type Role } from './accounts'

export const BASE_URL = 'http://localhost:5173'

/**
 * Sign in through the API and save the cookie where specs pick it up.
 *
 * Used by global-setup and by any spec that signs a role out: logout bumps the
 * account's token_version, which revokes EVERY session of that account,
 * including the saved one.
 */
export async function saveSession(role: Role): Promise<void> {
  const context = await request.newContext({ baseURL: BASE_URL })
  try {
    const response = await context.post('/api/auth/login', {
      data: { email: ACCOUNTS[role].email, password: e2ePassword() },
    })
    if (!response.ok()) {
      // Status only: the body could echo the request, and the request holds the password.
      throw new Error(
        `Login as ${role} failed with ${response.status()}. Run backend/scripts/e2e_seed.py first.`,
      )
    }
    await context.storageState({ path: storageStateFor(role) })
  } finally {
    await context.dispose()
  }
}
