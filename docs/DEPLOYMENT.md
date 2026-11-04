# Deployment guide

The frontend runs on Vercel and the API on Render. Vercel forwards `/api/*` to the API, so the browser sees a single origin and the session cookie is first-party.

```
Browser -> Vercel (static app + /api rewrite) -> Render (FastAPI) -> Supabase (PostgreSQL, Storage)
```

## Before you start

- Use a Supabase project for production that is separate from development and from the test database.
- Use a new database password. Copy the **Session pooler** URL and change the scheme to `postgresql+psycopg://`. URL-encode special characters in the password.
- If profile photos are enabled, create a **private** bucket in that project.

## 1. API on Render

1. New > Blueprint > select this repository. Render reads `render.yaml`.
2. Enter the variables marked `sync: false`:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Session pooler URL of the production project |
| `CORS_ORIGINS` | `["https://<your-app>.vercel.app"]` (JSON list, never `*`) |
| `TRUSTED_PROXY_HOPS` | `2` as a starting point; see "Client IP" below |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key. It stays on the server only |
| `SUPABASE_STORAGE_BUCKET` | Name of the private bucket |

3. Deploy. Check that `https://<service>.onrender.com/health` answers `{"status":"ok"}` and that `/docs` answers 404.
4. Create the first administrator with `python -m scripts.create_admin`, from the service's Shell tab. If your plan has no Shell, run it on your machine with `DATABASE_URL` set to the production URL for that one command.
5. If photos are enabled, confirm the bucket the same way: `python -m scripts.check_storage`.

If the service name was taken, Render adds a suffix to the URL. Update `destination` in `frontend/vercel.json` to match.

## 2. Frontend on Vercel

1. Add New > Project > select this repository.
2. Set **Root Directory** to `frontend`. Vercel detects Vite (build `npm run build`, output `dist`).
3. Deploy. Put the final URL in `CORS_ORIGINS` on Render.

## 3. Verify in production

Use the browser's developer tools on the Vercel URL:

- [ ] Login works and the request goes to `/api/auth/login` on the Vercel domain.
- [ ] The `tat_access_token` cookie shows `HttpOnly`, `Secure` and `SameSite=Lax`.
- [ ] Reloading a deep link such as `/empleados` keeps the page open.
- [ ] Logout removes the session and `/api/auth/me` answers 401.
- [ ] Six wrong passwords in a row answer 429 on the last attempt.

## 4. Client IP

The IP is used for login limits and audit records. `TRUSTED_PROXY_HOPS` says how many entries to count from the right of `X-Forwarded-For`, because entries further left can be invented by the client.

The right value depends on what Vercel and Render add, so confirm it after the first deploy:

1. Log in from a network whose public IP you know.
2. Open the Auditoría view and compare the recorded IP.
3. Adjust the variable if a proxy address appears instead of yours.

A wrong value is not a crash, but all users could share one IP and one login limit. A value that is too high can let clients choose their own IP.

## 5. Protect `main`

Settings > Rules > Rulesets > New branch ruleset, targeting the default branch:

- Require a pull request, with 0 required approvals.
- Require status checks: `backend` and `frontend`.
- Allow only squash merges.
- Block force pushes and restrict deletions.

## Known limits of the free plans

- Render stops idle services. The first request afterwards can take close to a minute, so open the app before a demo.
- Login limit counters live in memory and reset whenever the API restarts.
