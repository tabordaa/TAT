# TAT – Estado del proyecto

> Fuente de verdad para retomar el trabajo en cualquier sesión (Claude Code o Cowork).
> Actualízalo al cerrar cada sesión de trabajo. Última actualización: 8 oct 2026 (cierre Sprint 1).

## Sprint 1 (Iteration 1) – cerrado

| HU | Pts | Estado |
|---|---|---|
| 1.1 Login | 8 | Done. El CA03 (contraseña temporal) se trasladó a la HU-1.2 en DevOps |
| 1.3 Logout | 2 | Done |
| 2.1 Registro de empleado | 5 | Done tras `fix/72-employee-required-fields`: salario, correo y área obligatorios; unicidad de documento y correo solo entre ACTIVO |
| 2.2 Listado y búsqueda | 5 | Movida a Iteration 2 (no iniciada) |

Tests automatizados (QA #54 y #66) movidos a Iteration 2. Verificación hecha con smoke tests de API.

## Sprint 2 (Iteration 2) – arranque

1. HU-2.2: `GET /employees` con búsqueda (nombre/documento), filtro ACTIVO/INACTIVO y paginación + tabla con debounce.
2. QA con pytest para HU-1.1, 1.3 y 2.1. Decidir BD de pruebas (Supabase de pruebas o Postgres en Docker).
   Casos 2.1: creado, documento duplicado (409 `field=document_number`), correo duplicado (409 `field=email`),
   reingreso tras INACTIVO (201), faltan correo/área/salario (422), salario <= 0 (422), sin sesión (401).
3. Prueba manual en el navegador (:5173) del formulario con el campo salario y los 409 por campo.
4. Kevin: estudiar el código (ver "Plan de estudio").
5. Decidir qué hacer con las QA #54 y #66: siguen como hijas de HU cerradas (1.3 y 2.1); opción limpia:
   moverlas a una HU técnica del Sprint 2 ("Pruebas automatizadas de autenticación y empleados").

## Forma de trabajo (acordada el 8 oct)

- Herramienta: extensión de Claude Code en VS Code, output style **Learning** (en `.claude/settings.local.json`),
  modo de permisos normal (no auto). Kevin escribe el código; Claude guía y revisa como PR.
- `gh` instalado (v2.102.0, autenticado como `tabordaa`). En Git Bash no está en el PATH:
  usar `"/c/Program Files/GitHub CLI/gh.exe"`. El merge de PRs lo hace Kevin.

## Decisiones de arquitectura (y por qué)

- **JWT en cookie HttpOnly + SameSite=Lax**: el token no es accesible desde JS (XSS) y no viaja en POST cross-site (CSRF).
- **PyJWT + pwdlib (Argon2id)**: python-jose y passlib están sin mantenimiento / rotos con bcrypt moderno.
- **`users.token_version` + claim `ver`**: permite revocar JWT stateless en el logout (cierra sesión en todos los dispositivos; aceptado).
- **Supabase solo como PostgreSQL** (no Supabase Auth), vía Session pooler (IPv4). **RLS activado en cada tabla** para que la Data API pública (anon key) no exponga datos; el backend usa el rol `postgres`, que ignora RLS.
- **Empleados**: documento (tipo, número) y correo únicos **solo entre ACTIVO**, con índices únicos parciales (`WHERE status = 'ACTIVO'`) para permitir reingresos (HU-3.1) + chequeo previo para un 409 con `{field, message}`; salario `NUMERIC(12,2)` > 0 (nunca float); CHECK `end_date >= start_date`; el estado ACTIVO lo fija el servidor; `created_by_id` para auditoría.
- **Proxy de Vite `/api` → API** (y rewrite de Vercel en producción): un solo origen, la cookie es first-party.
- **Monorepo + GitHub Flow + squash merge**, Conventional Commits, `main` protegido.
- **Diseño**: pantallas de Google Stitch solo como inspiración; código escrito desde cero.

## Pendientes / deuda técnica (priorizado)

1. (Ver "Sprint 2 – arranque" arriba.)
2. Quién puede ver el salario: depende de la autorización por rol.
3. ruff + mypy --strict + GitHub Actions como status check obligatorio en `main`.
4. Autorización por rol (`require_role`, 403) cuando existan acciones solo-ADMIN.
5. Runtimes: Python 3.10 → 3.12; Node 20.16 → 22 LTS.
6. Logging de errores en el servidor.
7. Despliegue: Render (API) + Vercel (front) con rewrite `/api/*`.

## Recordatorios de Kevin

- [ ] **Proteger `main`**: hoy NO tiene branch protection ni rulesets (verificado el 8 oct; repo público, Kevin es admin).
      Settings → Rules → Rulesets → New branch ruleset, target `main` (Include default branch):
      - Require a pull request before merging: ✅ con **Required approvals = 0**. NUNCA ≥ 1: GitHub no
        permite aprobar el propio PR y, siendo el único desarrollador, ningún PR podría mergearse.
      - Allowed merge methods: solo **Squash**.
      - Block force pushes: ✅ · Restrict deletions: ✅
      - Require status checks: ❌ por ahora; activarlo cuando exista el CI (ruff, mypy, typecheck).
      - Bypass list: vacía (si Kevin se agrega, las reglas dejan de aplicarle).
      Validación: mergear un PR con `gh pr merge --squash` y comprobar que un `git push` directo a `main` es rechazado.
- [ ] Integración Azure Boards ↔ GitHub (`AB#<id>` en PRs).
- [ ] Activar GitHub Student Developer Pack.
- [ ] Activar "Automatically delete head branches" en GitHub y borrar ramas viejas.
- [x] Configurar el MCP de Azure DevOps en Claude Code.

## Plan de estudio (Kevin escribió poco del código del Sprint 1)

Recorrer y luego reescribir de memoria, en este orden:
1. `backend/app/core/security.py` – Argon2, creación/verificación de JWT.
2. `backend/app/api/deps.py` – `get_current_user`, revocación con `token_version`.
3. `backend/app/api/auth.py` – login (anti-enumeración, cookie), me, logout.
4. `backend/app/api/employees.py` – 409 y por qué la unicidad vive en la BD.
5. `frontend/src/auth/AuthProvider.tsx` – restaurar sesión con `/auth/me`, interceptor 401.
