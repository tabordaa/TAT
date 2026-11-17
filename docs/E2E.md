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

## How sessions work

`e2e/global-setup.ts` signs in once per role through the API and saves the cookie in `e2e/.auth/`. Specs pick a role with `test.use({ storageState: storageStateFor('HR') })`, which keeps the run far below the login rate limits. A spec that signs out must call `saveSession(role)` afterwards: logout revokes every session of that account.

## CI

The `e2e` job in `.github/workflows/ci.yml` uses its own PostgreSQL service, runs the migrations and the seed, then `npx playwright test`. When it fails, the HTML report and traces are uploaded as the `playwright-report` artifact.
