# Browser tests (Playwright)

The specs live in `frontend/e2e/` and drive the real app (Vite + FastAPI + PostgreSQL) in Chromium.

## Test accounts

`backend/scripts/e2e_seed.py` creates or resets one account per role, each linked to an employee with a contract in force:

| Role | Email |
|---|---|
| ADMIN | `laura.restrepo@tat.example.com` |
| HR | `andres.cardona@tat.example.com` |
| MANAGER | `catalina.mejia@tat.example.com` |
| EMPLOYEE | `juan.ospina@tat.example.com` (one year of service) |

The `@tat.example.com` domain (reserved by RFC 2606) is the only thing that marks them. The seed touches no other row and refuses to run with `ENVIRONMENT=production`. All four share the password in `E2E_PASSWORD`.

## Run locally (PowerShell)

```powershell
# once: the browser and the password file (git-ignored)
cd frontend
npx playwright install chromium
# create frontend\e2e\.env.e2e with one line: E2E_PASSWORD=<at least 12 characters>

# seed the accounts (from backend\, with the venv active)
cd ..\backend
$env:E2E_PASSWORD = (Get-Content ..\frontend\e2e\.env.e2e).Split('=', 2)[1]
python -m scripts.e2e_seed
Remove-Item Env:E2E_PASSWORD

# run the suite (starts uvicorn and Vite unless they are already running)
cd ..\frontend
npm run e2e
npx playwright show-report        # HTML report of the last run
```

Locally the suite uses the development database, so every run adds a few records (realistic names, no prefix).

- The profile photo spec runs only with `$env:E2E_STORAGE = "1"`, because it uploads to the real Supabase bucket.
- The login rate limiter lives in the API's memory and counts failures per IP (30 in 15 minutes). A run causes about a dozen on purpose. When Playwright starts the API itself, every run begins from zero. If you keep your own `fastapi dev` running, restart it after two or three runs.

## Specs

| File | Covers |
|---|---|
| `smoke.spec.ts` | Every role's home screen, login and logout (HU-1.1, HU-1.3) |
| `sprint3/01-register-with-account.spec.ts` | Employee with account, audit trail (HU-1.4, HU-5.1) |
| `sprint3/02-first-access.spec.ts` | Forced change of the temporary password (HU-1.2) |
| `sprint3/03-my-profile.spec.ts` | My profile, contact details, photo (HU-2.6, HU-2.7) |
| `sprint3/04-password-reset.spec.ts` | Reset by an ADMIN (HU-1.5) |
| `sprint3/05-contracts.spec.ts` | Contract assignment and expiring contracts (HU-3.1, HU-3.2) |
| `sprint3/06-termination.spec.ts` | Two-step termination, sessions end (HU-3.3) |
| `sprint3/07-rehire.spec.ts` | Rehire without access until a reset (HU-3.1) |
| `sprint3/08-manager.spec.ts` | Read-only MANAGER, API answers 403 |
| `sprint3/09-login-rate-limit.spec.ts` | Too many failed logins |

## How sessions work

`e2e/global-setup.ts` signs in once per role through the API and saves the cookie in `e2e/.auth/`. Specs pick a role with `test.use({ storageState: storageStateFor('HR') })`, which keeps the run far below the login rate limits. A spec that signs out must call `saveSession(role)` afterwards: logout revokes every session of that account.

## CI

The `e2e` job in `.github/workflows/ci.yml` uses its own PostgreSQL service, runs the migrations and the seed, then `npx playwright test`. When it fails, the HTML report and traces are uploaded as the `playwright-report` artifact.
