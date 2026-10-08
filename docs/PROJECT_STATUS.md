# TAT – Estado del proyecto

> Fuente de verdad para retomar el trabajo en cualquier sesión (Claude Code o Cowork).
> Actualízalo al cerrar cada sesión de trabajo. Última actualización: 7 oct 2026 (cierre Sprint 1).

## ⚠️ LO PRIMERO: cerrar HU-1.3 y HU-2.1

Verificado el 7 oct (Claude Code):
- [x] `alembic upgrade head` aplicó `9a1c4e7b2d10` y `c3e8f2a61b47` en Supabase.
- [x] `npm run typecheck` sin errores.
- [x] Smoke test de API (14/14): 401 sin sesión, login malo con mismo mensaje, cookie HttpOnly+Lax,
      sin `hashed_password`, empleado 201 ACTIVO, duplicado 409, fechas 422, `status` del cliente 422,
      logout 204 idempotente, token viejo tras logout 401, `created_by_id` y RLS en `employees`.
- [x] Commits y push: `feat/6-logout-token-revocation` (HU-1.3) y `feat/12-register-employee` (HU-2.1, apilada sobre la 6).

Pendiente:
1. Abrir/mergear PRs en orden: primero HU-1.3 (#6), luego HU-2.1 (#12) — la migración de employees depende de la de token_version.
2. Prueba manual en el navegador (:5173): mensaje verde tras registrar, 409 bajo el campo, redirección al login tras logout.
3. Kevin: estudiar el código (ver "Plan de estudio") — se commiteó sin que lo escribiera él.
5. Escribir tests con pytest (tareas QA de HU-1.1, 1.3 y 2.1): login ok/credenciales malas/sin sesión,
   logout revoca el token anterior, empleado creado/duplicado (409)/fechas inválidas (422)/sin sesión (401).
   Requiere decidir BD de pruebas (p. ej. un proyecto Supabase de pruebas o Postgres local en Docker).
6. Commits / PRs: uno por HU (`feat(auth): revoke tokens on logout with token_version`,
   `feat(employees): register employees with unique document validation`), squash merge.
7. Actualizar el tablero (pasar tareas a Done) y este archivo.

## Sprint 1 (20 pts) – resultado

| HU | Pts | Estado |
|---|---|---|
| 1.1 Login | 8 | Funciona y está en `main` (probado manualmente). Falta QA automatizada |
| 1.3 Logout | 2 | Verificado (smoke test API) y en PR `feat/6-logout-token-revocation`. Falta QA automatizada |
| 2.1 Registro de empleado | 5 | Verificado (smoke test API) y en PR `feat/12-register-employee`. Falta QA automatizada |
| 2.2 Listado y búsqueda | 5 | No iniciada → pasa al Sprint 2 |

## Decisiones de arquitectura (y por qué)

- **JWT en cookie HttpOnly + SameSite=Lax**: el token no es accesible desde JS (XSS) y no viaja en POST cross-site (CSRF).
- **PyJWT + pwdlib (Argon2id)**: python-jose y passlib están sin mantenimiento / rotos con bcrypt moderno.
- **`users.token_version` + claim `ver`**: permite revocar JWT stateless en el logout (cierra sesión en todos los dispositivos; aceptado).
- **Supabase solo como PostgreSQL** (no Supabase Auth), vía Session pooler (IPv4). **RLS activado en cada tabla** para que la Data API pública (anon key) no exponga datos; el backend usa el rol `postgres`, que ignora RLS.
- **Empleados**: documento único por (tipo, número) garantizado por la BD (UNIQUE) + chequeo previo para dar un 409 amigable; CHECK `end_date >= start_date`; el estado ACTIVO lo fija el servidor; `created_by_id` para auditoría.
- **Proxy de Vite `/api` → API** (y rewrite de Vercel en producción): un solo origen, la cookie es first-party.
- **Monorepo + GitHub Flow + squash merge**, Conventional Commits, `main` protegido.
- **Diseño**: pantallas de Google Stitch solo como inspiración; código escrito desde cero.

## Pendientes / deuda técnica (priorizado)

1. (Ver sección "LO PRIMERO" arriba.)
2. HU-2.2: `GET /employees` con búsqueda y paginación + tabla con debounce.
3. ruff + mypy --strict + GitHub Actions como status check obligatorio en `main`.
4. Autorización por rol (`require_role`, 403) cuando existan acciones solo-ADMIN.
5. Runtimes: Python 3.10 → 3.12; Node 20.16 → 22 LTS.
6. Logging de errores en el servidor.
7. Despliegue: Render (API) + Vercel (front) con rewrite `/api/*`.

## Recordatorios de Kevin

- [ ] Integración Azure Boards ↔ GitHub (`AB#<id>` en PRs).
- [ ] Activar GitHub Student Developer Pack.
- [ ] Activar "Automatically delete head branches" en GitHub y borrar ramas viejas.
- [ ] Configurar el MCP de Azure DevOps en Claude Code.

## Plan de estudio (Kevin escribió poco del código del Sprint 1)

Recorrer y luego reescribir de memoria, en este orden:
1. `backend/app/core/security.py` – Argon2, creación/verificación de JWT.
2. `backend/app/api/deps.py` – `get_current_user`, revocación con `token_version`.
3. `backend/app/api/auth.py` – login (anti-enumeración, cookie), me, logout.
4. `backend/app/api/employees.py` – 409 y por qué la unicidad vive en la BD.
5. `frontend/src/auth/AuthProvider.tsx` – restaurar sesión con `/auth/me`, interceptor 401.
