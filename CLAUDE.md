# TAT · Tracking and Talent

HR management system (university final project, Ingeniería de Software II – Pascual Bravo).
Owner: Kevin (4 yrs Power Platform, learning React/TS, Python/FastAPI). Preparing for Mid/Senior interviews.

**At the start of every session, read `docs/PROJECT_STATUS.md`** (sprint status, decisions, pending work, study plan).
Update it at the end of a session when something important changes.

## How to work with me (MOST IMPORTANT)

- **Learning comes first.** Act as a Tech Lead: explain the *why* (architecture, security, trade-offs) before the *how*.
- **I write the code by default.** Give me guidance, signatures and hints, then review what I write like a PR.
  Only write code yourself when I explicitly ask for it (e.g. boilerplate or deadline pressure).
- When you do write code: keep it small, explain each file, and ask me 1–2 review questions per file before I commit.
- Never change files I didn't ask you to change. If I say "no hagas cambios", only teach.
- Answer in Spanish; code, identifiers and commit messages in English.
- I'm on Windows + PowerShell: give PowerShell-compatible commands and full paths.

## Stack

- **backend/**: Python, FastAPI, SQLAlchemy 2 (sync), psycopg 3, Alembic, pydantic-settings, PyJWT, pwdlib (Argon2). DB: PostgreSQL on Supabase (Session pooler).
- **frontend/**: React 19 + TypeScript (strict) + Vite, react-router 7, axios.
- Deploy target: Vercel (front) + Render (back), with a Vercel rewrite `/api/*` → API so the browser sees one origin.

## Commands (PowerShell)

```powershell
# backend (from backend/, with .venv active)
fastapi dev app/main.py                       # API on http://localhost:8000 (/docs)
alembic revision --autogenerate -m "msg"      # new migration (ALWAYS review the generated file)
alembic upgrade head
python -m scripts.create_admin                # first ADMIN user

# frontend (from frontend/)
npm run dev                                   # http://localhost:5173 (proxies /api → 127.0.0.1:8000)
npm run typecheck
```

Before saying something works, run the relevant check (typecheck, tests, endpoint call).

## Non-negotiable rules

- **Auth**: JWT only in an `HttpOnly` cookie (`SameSite=Lax`, `Secure` in prod). Never localStorage/sessionStorage.
- **CORS**: explicit origins + `allow_credentials=True`. Never `"*"`.
- **Secrets** only in `backend/.env` (git-ignored). Use `SecretStr`. Never log or return secrets or internal errors.
- **Same error message** for unknown email and wrong password (no user enumeration).
- **Frontend is TypeScript strict only**. No `any`, no JS files. Use `import type` for types.
- **Server validates everything**; client validation is UX only.
- Every new table: Alembic migration + `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` (Supabase Data API exposure).
- ORM models (`app/models`) ≠ API schemas (`app/schemas`). Responses never include `hashed_password`.
- Do not reuse code from `../employee-management` (old MVP).

## Git

- GitHub Flow: `main` is protected; one short branch per task: `<type>/<azure-id>-<short-desc>`.
- Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`); PR title = squash commit message.
- Commit or stash before switching branches.
- Link work items with `AB#<id>` in the PR description.

## Scrum (Azure DevOps, Agile process)

Epic → Feature → User Story → Task. Task titles prefixed `BE:`, `FE:` or `QA:`, estimated in hours.
Sprint 1 (20 pts): HU-1.1 Login (8), HU-1.3 Logout (2), HU-2.1 Registro de empleado (5), HU-2.2 Listado y búsqueda (5).
A story is Done only when backend + frontend + tests meet its acceptance criteria.

## Known tech debt

See `docs/PROJECT_STATUS.md`. Note: the local venv is Python 3.10 (no `datetime.UTC`, no `typing.Self`)
until it is upgraded to 3.12.
