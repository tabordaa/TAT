import { ROLES } from './accounts'
import { saveSession } from './session'

// Signs in ONCE per role through the API and saves the cookie. Specs reuse it,
// so a full run sends a handful of logins instead of one per test, far below
// the per-account and per-IP rate limits of POST /auth/login.
export default async function globalSetup(): Promise<void> {
  for (const role of ROLES) {
    await saveSession(role)
  }
}
