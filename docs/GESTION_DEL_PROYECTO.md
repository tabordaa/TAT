# Gestión del proyecto TAT

Este documento reúne la planeación y el seguimiento del proyecto tal como se registraron en **Azure DevOps** (proyecto `TAT`, proceso Agile con Scrum): épicas, historias de usuario con sus criterios de aceptación, tareas con horas y sprints. Se generó directamente desde los work items del tablero.

## 1. Cómo se trabajó

- **Jerarquía:** Épica → Feature → Historia de usuario → Tarea.
- **Historias** redactadas como *Como / Quiero / Para*, con criterios de aceptación numerados (CA01, CA02…) y estimadas en puntos de historia.
- **Tareas** con prefijo según la capa (`BACK_`, `FRONT_`, `QA_`), estimadas en horas; al cerrarlas se registra el trabajo completado.
- **Sprints de dos semanas.** Cada historia avanza por *Nueva → Activa → Resuelta → Cerrada*. *Resuelta* significa que el desarrollo y las pruebas automatizadas cumplen los criterios de aceptación; *Cerrada*, que además se validó manualmente en la aplicación.
- **Definición de terminado:** backend, frontend y pruebas cumplen los criterios de aceptación, el CI está en verde y el cambio entró a `main` por pull request enlazado a su tarea (`AB#<id>`).

## 2. Resumen por sprint

| Sprint | Fechas | Historias | Puntos planeados | Puntos terminados | Tareas | Horas registradas |
|---|---|:-:|:-:|:-:|:-:|:-:|
| Sprint 1 | 23 sep – 7 oct 2026 | 3 | 15 | 15 | 20 | 45 |
| Sprint 2 | 7 – 21 oct 2026 | 4 | 15 | 15 | 17 | 36 |
| Sprint 3 | 21 oct – 4 nov 2026 | 9 | 28 | 25 | 34 | 80.5 |
| Sprint 4 | 4 – 18 nov 2026 | 7 | 25 | 25 | 28 | 80.5 |
| Sprint 5 | 18 nov – 2 dic 2026 | 6 | 18 | 16 | 26 | 71 |
| Transversal | Todo el proyecto | 2 | 6 | 3 | 7 | 14 |
| **Total** | | **31** | **107** | **99** | **132** | **327** |

*Transversal* agrupa el trabajo de plataforma y calidad (roles, pruebas, despliegue) que acompañó a varios sprints.

## 3. Backlog por épica

### 1. Gestión de identidad y seguridad

| ID | Historia de usuario | Puntos | Sprint | Estado |
|---|---|:-:|---|---|
| 4 | Autenticación de usuarios · [1.1. Inicio de sesión](#hu-11-inicio-de-sesión) | 8 | Sprint 1 | Cerrada |
| 5 | Autenticación de usuarios · [1.2. Cambio de contraseña en primer acceso](#hu-12-cambio-de-contraseña-en-primer-acceso) | 3 | Sprint 3 | Resuelta |
| 6 | Autenticación de usuarios · [1.3. Cierre de sesión](#hu-13-cierre-de-sesión) | 2 | Sprint 1 | Cerrada |
| 8 | Gestión de cuentas (administración) · [1.4. Creación de cuentas de acceso](#hu-14-creación-de-cuentas-de-acceso) | 5 | Sprint 2 | Resuelta |
| 9 | Gestión de cuentas (administración) · [1.5. Reset manual de contraseña](#hu-15-reset-manual-de-contraseña) | 2 | Sprint 3 | Resuelta |
| 78 | Gestión de cuentas (administración) · [1.6. Roles y autorización](#hu-16-roles-y-autorización) | 3 | Sin sprint | Cerrada |

### 2. Gestión de empleados

| ID | Historia de usuario | Puntos | Sprint | Estado |
|---|---|:-:|---|---|
| 12 | Administración de perfiles · [2.1. Registro de nuevo empleado (onboarding)](#hu-21-registro-de-nuevo-empleado-onboarding) | 5 | Sprint 1 | Cerrada |
| 13 | Administración de perfiles · [2.2. Búsqueda de empleados](#hu-22-búsqueda-de-empleados) | 5 | Sprint 2 | Resuelta |
| 14 | Administración de perfiles · [2.3. Visualización detallada de expediente](#hu-23-visualización-detallada-de-expediente) | 3 | Sprint 2 | Resuelta |
| 15 | Administración de perfiles · [2.4. Actualización de datos laborales](#hu-24-actualización-de-datos-laborales) | 5 | Sprint 4 | Resuelta |
| 16 | Administración de perfiles · [2.5. Visualización de historial de cambios salariales](#hu-25-visualización-de-historial-de-cambios-salariales) | 2 | Sprint 4 | Resuelta |
| 18 | Portal del empleado · [2.6. Visualización de mi perfil personal](#hu-26-visualización-de-mi-perfil-personal) | 3 | Sprint 3 | Resuelta |
| 19 | Portal del empleado · [2.7. Actualización de datos personales](#hu-27-actualización-de-datos-personales) | 3 | Sprint 3 | Resuelta |
| 163 | Portal del empleado · [2.8. Certificado laboral descargable](#hu-28-certificado-laboral-descargable) | 3 | Sprint 5 | Resuelta |

### 3. Gestión de contratos

| ID | Historia de usuario | Puntos | Sprint | Estado |
|---|---|:-:|---|---|
| 22 | Ciclo de vida del contrato · [3.1. Asignación de contrato (ingreso / reingreso)](#hu-31-asignación-de-contrato-ingreso--reingreso) | 3 | Sprint 3 | Resuelta |
| 23 | Ciclo de vida del contrato · [3.2. Alertas de vencimiento próximo de contratos](#hu-32-alertas-de-vencimiento-próximo-de-contratos) | 3 | Sprint 3 | Resuelta |
| 24 | Ciclo de vida del contrato · [3.3. Finalización de contrato](#hu-33-finalización-de-contrato) | 3 | Sprint 3 | Resuelta |

### 4. Gestión de vacaciones

| ID | Historia de usuario | Puntos | Sprint | Estado |
|---|---|:-:|---|---|
| 27 | Proceso de solicitud y aprobación · [4.1. Solicitud de vacaciones (rol empleado)](#hu-41-solicitud-de-vacaciones-rol-empleado) | 5 | Sprint 4 | Resuelta |
| 28 | Proceso de solicitud y aprobación · [4.2. Aprobación o rechazo de vacaciones (talento humano)](#hu-42-aprobación-o-rechazo-de-vacaciones-talento-humano) | 3 | Sprint 4 | Resuelta |
| 159 | Proceso de solicitud y aprobación · [4.5. Cancelar mi solicitud de vacaciones](#hu-45-cancelar-mi-solicitud-de-vacaciones) | 3 | Sprint 5 | Resuelta |
| 161 | Proceso de solicitud y aprobación · [4.7. Notificaciones de solicitudes de vacaciones](#hu-47-notificaciones-de-solicitudes-de-vacaciones) | 5 | Sprint 5 | Resuelta |
| 30 | Saldos y visualización · [4.3. Control de saldo de vacaciones automático](#hu-43-control-de-saldo-de-vacaciones-automático) | 3 | Sprint 4 | Resuelta |
| 31 | Saldos y visualización · [4.4. Calendario de ausencias](#hu-44-calendario-de-ausencias) | 5 | Sprint 4 | Resuelta |
| 160 | Saldos y visualización · [4.6. Festivos de Colombia en el conteo de días](#hu-46-festivos-de-colombia-en-el-conteo-de-días) | 3 | Sprint 5 | Resuelta |
| 162 | Saldos y visualización · [4.8. Calendario de ausencias filtrado por área](#hu-48-calendario-de-ausencias-filtrado-por-área) | 2 | Sprint 5 | Resuelta |

### 5. Reportes y auditoría

| ID | Historia de usuario | Puntos | Sprint | Estado |
|---|---|:-:|---|---|
| 34 | Trazabilidad (log de auditoría) · [5.1. Log de actividad de usuarios](#hu-51-log-de-actividad-de-usuarios) | 5 | Sprint 3 | Resuelta |
| 36 | Reportes y exportación · [5.2. Exportar lista de empleados a excel/csv](#hu-52-exportar-lista-de-empleados-a-excelcsv) | 2 | Sprint 4 | Resuelta |
| 164 | Reportes y exportación · [5.3. Exportar la lista de empleados a Excel (.xlsx)](#hu-53-exportar-la-lista-de-empleados-a-excel-xlsx) | 2 | Sprint 5 | Nueva |

### 6. Dashboard gerencial

| ID | Historia de usuario | Puntos | Sprint | Estado |
|---|---|:-:|---|---|
| 39 | Métricas en tiempo real · [6.1. Visualización de indicadores generales](#hu-61-visualización-de-indicadores-generales) | 2 | Sprint 2 | Resuelta |
| 40 | Métricas en tiempo real · 6.2. Alerta de contratos por vencer *(sus criterios pasaron a la HU 3.2)* | — | Sin sprint | Eliminada |

### 7. Plataforma y calidad

| ID | Historia de usuario | Puntos | Sprint | Estado |
|---|---|:-:|---|---|
| 77 | Pruebas automatizadas · [7.1. Pruebas automatizadas de autenticación y empleados](#hu-71-pruebas-automatizadas-de-autenticación-y-empleados) | 3 | Sin sprint | Activa |
| 79 | Despliegue y CI · [7.2. Despliegue (Render y Vercel) e integración continua](#hu-72-despliegue-render-y-vercel-e-integración-continua) | 3 | Sprint 3 | Activa |

## 4. Detalle de las historias de usuario

### HU 1.1. Inicio de sesión

`#4` · Sprint 1 · 8 puntos · Cerrada

**Como** usuario del sistema (Admin, gerente o empleado)  
**Quiero** iniciar sesión con mi correo y contraseña  
**Para** acceder a las funcionalidades según mi rol de forma segura

**Criterios de aceptación**

- **CA01:** Si las credenciales son incorrectas, se muestra un mensaje de error claro.
- **CA02:** Si el login es exitoso, redirige al Dashboard correspondiente a su rol.
- El criterio de contraseña temporal en el primer login se trasladó a la HU 1.2.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#41` BACK_Instalar librerías de auth | 1 | 1 | Cerrada |
| `#42` BACK_Crear modelo user con SQLAlchemy | 2 | 2 | Cerrada |
| `#43` BACK_Implementar utilidades de hashing (Argon2id) | 1 | 1 | Cerrada |
| `#44` BACK_Implementar generación de token JWT | 2 | 2 | Cerrada |
| `#45` BACK_Crear endpoint POST /auth/login (con HttpOnly Cookie) | 5 | 5 | Cerrada |
| `#46` BACK_Crear dependencia get_current_user para proteger rutas | 2 | 2 | Cerrada |
| `#47` FRONT_Crear pagina login.tsx y diseño de UI | 3 | 3 | Cerrada |
| `#48` FRONT_Configurar cliente HTTP (axios) y authService.ts | 1 | 1 | Cerrada |
| `#49` FRONT_Crear AuthContext.tsx y configurar Axios con credenciales | 4 | 4 | Cerrada |
| `#50` FRONT_Implementar componente ProtectedRoute.tsx | 1 | 1 | Cerrada |

### HU 1.2. Cambio de contraseña en primer acceso

`#5` · Sprint 3 · 3 puntos · Resuelta

**Como** empleado que acaba de recibir credenciales temporales  
**Quiero** ser obligado a cambiar mi contraseña en el primer login  
**Para** garantizar que solo yo conozca mi clave de acceso

**Criterios de aceptación**

- **CA01:** El sistema no permite navegar a ninguna otra ruta hasta que se cambie la contraseña
- **CA02:** La nueva contraseña debe contener como mínimo 8 caracteres
- **CA03:** La nueva contraseña no puede ser igual a la contraseña temporal
- **CA04:** Si es el primer login (contraseña temporal), el sistema redirige obligatoriamente a la pantalla de cambio de contraseña (trasladado desde HU 1.1).

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#107` BACK_Endpoint de cambio de contraseña y bloqueo del resto de la API | 4 | 4 | Cerrada |
| `#108` FRONT_Pantalla de cambio obligatorio y redirección | 3 | 3 | Cerrada |
| `#109` QA_Pruebas de cambio de contraseña | 2 | 2 | Cerrada |

### HU 1.3. Cierre de sesión

`#6` · Sprint 1 · 2 puntos · Cerrada

**Como** cualquier usuario autenticado  
**Quiero** poder cerrar mi sesión en cualquier momento  
**Para** proteger mi cuenta al dejar de usar el sistema

**Criterios de aceptación**

- **CA01:** El botón de cerrar cesión debe estar visible en el menú principal
- **CA02:** Al cerrar sesión, el sistema debe eliminar el token de acceso localmente y redirigir a la pantalla del login
- **CA03:** Si el usuario intenta volver atrás con el navegador tras cerrar sesión, el sistema debe proteger las rutas.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#51` BACK_Endpoint POST /auth/logout que elimina la cookie HttpOnly | 1 | 1 | Cerrada |
| `#52` FRONT_Botón "Cerrar sesión" visible en el layout: llama al API, limpia el estado y redirige al login | 1.5 | 1.5 | Cerrada |
| `#53` FRONT_Manejo global de 401 con un interceptor de Axios: si el token expira, limpiar la sesión y volver al login | 1.5 | 1.5 | Cerrada |

### HU 1.4. Creación de cuentas de acceso

`#8` · Sprint 2 · 5 puntos · Resuelta

**Como** administrador del sistema  
**Quiero** crear cuentas de acceso al mismo tiempo que registro a un empleado  
**Para** provisionar sus credenciales desde el primer día

**Criterios de aceptación**

- **CA01:** Al momento de la creación, se le asigna un rol al empleado (admin, gerente, empleado)
- **CA02:** El sistema genera una contraseña temporal de un solo uso
- **CA03:** La cuenta queda marcada como "requiere cambio de contraseña en el primer login"

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#89` BACK_Crear cuenta con rol y contraseña temporal al registrar empleado | 4 | 4 | Cerrada |
| `#90` BACK_Marca de cambio de contraseña obligatorio | 1 | 1 | Cerrada |
| `#91` FRONT_Selector de rol en el formulario de registro | 3 | 3 | Cerrada |
| `#92` FRONT_Mostrar la contraseña temporal una sola vez | 2 | 2 | Cerrada |
| `#93` QA_Pruebas de creación de cuentas | 2 | 2 | Cerrada |

### HU 1.5. Reset manual de contraseña

`#9` · Sprint 3 · 2 puntos · Resuelta

**Como** administrador del sistema  
**Quiero** poder resetear la contraseña de cualquier usuario desde el panel  
**Para** desbloquear el acceso de empleados que olvidaron sus credenciales

**Criterios de aceptación**

- **CA01:** El botón de resetear solo debe ser visible para usuarios con el rol admin
- **CA02:** Al ejecutar la acción, se invalida la contraseña actual y se genera una temporal
- **CA03:** El estado del usuario vuelve a "requiere cambio de contraseña"

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#110` BACK_Endpoint de reset de contraseña (solo ADMIN) | 2 | 2 | Cerrada |
| `#111` FRONT_Botón de reset visible solo para ADMIN | 1.5 | 1.5 | Cerrada |
| `#112` QA_Pruebas de reset de contraseña | 1.5 | 1.5 | Cerrada |

### HU 1.6. Roles y autorización

`#78` · Sin sprint · 3 puntos · Cerrada

**Como** administrador del sistema  
**Quiero** que cada usuario tenga un rol y que el API restrinja las acciones según ese rol  
**Para** que cada persona solo acceda a lo que le corresponde

**Criterios de aceptación**

- **CA01:** Existen cuatro roles, con los valores ADMIN, MANAGER, HR y EMPLOYEE en el código y la base de datos; en la interfaz se muestran como Administrador, Gerente, Recursos Humanos y Empleado
- **CA02:** Sin sesión el API responde 401; con sesión pero sin el rol requerido responde 403
- **CA03:** Un usuario puede quedar vinculado a un registro de empleado (vínculo opcional)
- **CA04:** Los usuarios existentes (ADMIN y HR) conservan su acceso sin migración de datos

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#85` BACK_Enum de roles (agregar MANAGER y EMPLOYEE) | 1 | 1 | Cerrada |
| `#86` BACK_Dependencia require_role (401/403) | 2 | 2 | Cerrada |
| `#87` BACK_Vínculo user - employee (migración con RLS) | 2 | 2 | Cerrada |
| `#88` QA_Pruebas de autorización por rol | 2 | 2 | Cerrada |

### HU 2.1. Registro de nuevo empleado (onboarding)

`#12` · Sprint 1 · 5 puntos · Cerrada

**Criterios de aceptación**

- **CA01:** El formulario debe requerir campos obligatorios: Nombre, cédula, correo, cargo, departamento, fecha de inicio, salario
- **CA02:** El sistema debe validar que el número de cedula y el correo no estén registrados como activos
- **CA03:** El estado del nuevo registro debe ser "activo" por defecto

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#61` BACK_Modelo Employee y migración | 3 | 3 | Cerrada |
| `#62` BACK_Schemas Pydantic de creación y respuesta con validaciones | 2 | 2 | Cerrada |
| `#63` BACK_Endpoint POST /employees protegido | 3 | 3 | Cerrada |
| `#64` FRONT_Formulario de registro con validación en cliente | 4 | 4 | Cerrada |
| `#65` FRONT_Integración del formulario con POST /employees | 2 | 2 | Cerrada |
| `#72` BACK_Salario, correo y departamento obligatorios y unicidad de cédula/correo entre empleados activos | 3 | 3 | Cerrada |
| `#73` FRONT_Campos salario, correo y departamento obligatorios en el formulario de registro | 2 | 2 | Cerrada |

### HU 2.2. Búsqueda de empleados

`#13` · Sprint 2 · 5 puntos · Resuelta

**Como** coordinador de recursos humanos  
**Quiero** buscar y filtrar la lista de empleados por nombre o documento y por estado  
**Para** encontrar rápidamente el expediente que necesito

**Criterios de aceptación**

- **CA01:** La tabla debe mostrar columnas clave como: nombre, cédula, cargo, estado
- **CA02:** Debe existir un buscador por nombre y documento que filtre resultados en tiempo real
- **CA03:** Debe existir un filtro para ver inactivos y activos
- **CA04:** La lista se pagina (no carga todos los empleados de una vez) y requiere sesión activa

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#67` BACK_Endpoint GET /employees con búsqueda y paginación | 3 | 3 | Cerrada |
| `#68` BACK_Índices de búsqueda en employees | 1 | 1 | Cerrada |
| `#69` FRONT_Tabla de empleados | 4 | 4 | Cerrada |
| `#70` FRONT_Búsqueda en tiempo real con debounce | 2 | 2 | Cerrada |
| `#71` QA_Pruebas de listado y búsqueda | 2 | 2 | Cerrada |

### HU 2.3. Visualización detallada de expediente

`#14` · Sprint 2 · 3 puntos · Resuelta

**Como** coordinador de recursos humanos,  
**Quiero** hacer clic en un empleado de la lista para ver su perfil completo,  
**Para** consultar su información de contacto, salario y detalles contractuales.

**Criterios de aceptación**

- **CA01:** Debe mostrar todos los campos registrados, agrupados de forma lógica (Datos personales, Datos laborales).
- **CA02:** Debe mostrar el estado actual del empleado y un avatar con sus iniciales (la carga de foto de perfil queda fuera de este sprint).
- **CA03:** Si el empleado no existe, el sistema muestra un mensaje claro (la API responde 404).
- **CA04:** Requiere sesión activa (la API responde 401 sin sesión).

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#81` BACK_Endpoint GET /employees/{id} | 2 | 2 | Cerrada |
| `#82` FRONT_Página de detalle con secciones y badge de estado | 4 | 4 | Cerrada |
| `#83` FRONT_Navegación desde la tabla al detalle | 1 | 1 | Cerrada |
| `#84` QA_Pruebas del detalle (200, 404, 401) | 1 | 1 | Cerrada |

### HU 2.4. Actualización de datos laborales

`#15` · Sprint 4 · 5 puntos · Resuelta

**Como** administrador del sistema,  
**Quiero** poder editar los datos laborales de un empleado (ej: ascenso o aumento salarial),  
**Para** mantener la base de datos sincronizada con la realidad.

**Criterios de aceptación**

- **CA01:** El Admin puede editar campos restringidos como Salario, Departamento y Cargo.
- **CA02:** Al cambiar el salario, el sistema debe registrar el cambio automáticamente en el historial salarial.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#131` BACK_Tabla salary_changes y endpoint de edición de datos laborales | 5 | 5 | Cerrada |
| `#132` FRONT_Formulario de edición de datos laborales en el expediente | 4 | 4 | Cerrada |
| `#133` QA_Pruebas de edición de datos laborales | 2 | 2 | Cerrada |

### HU 2.5. Visualización de historial de cambios salariales

`#16` · Sprint 4 · 2 puntos · Resuelta

**Como** gerente o administrador,  
**Quiero** ver un histórico de todos los cambios de salario que ha tenido un empleado,  
**Para** auditar y analizar la evolución de su compensación económica en la empresa.

**Criterios de aceptación**

- **CA01:** En el perfil del empleado debe existir una pestaña o sección de "Historial Salarial".
- **CA02:** Cada registro debe mostrar: Salario Anterior, Salario Nuevo, y Fecha del cambio.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#134` BACK_Endpoint de historial salarial | 2 | 2 | Cerrada |
| `#135` FRONT_Sección Historial salarial en el expediente | 2 | 2 | Cerrada |
| `#136` QA_Pruebas de historial salarial | 1.5 | 1.5 | Cerrada |

### HU 2.6. Visualización de mi perfil personal

`#18` · Sprint 3 · 3 puntos · Resuelta

**Como** empleado,  
**Quiero** poder ingresar al sistema y ver mi propio expediente,  
**Para** validar que mis datos y condiciones laborales actuales estén correctos.

**Criterios de aceptación**

- **CA01:** Al iniciar sesión como Empleado, el usuario es redirigido a su propia vista de perfil.
- **CA02:** El empleado NO debe poder ver el listado de otros empleados ni modificar sus datos laborales (Salario, Cargo).

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#113` BACK_Acceso de solo lectura para MANAGER | 2 | 2 | Cerrada |
| `#114` BACK_Endpoint GET /me/employee | 1.5 | 1.5 | Cerrada |
| `#115` FRONT_Vista Mi perfil, redirección y menú por rol | 3 | 3 | Cerrada |
| `#116` QA_Pruebas de Mi perfil y autorización por rol | 2 | 2 | Cerrada |

### HU 2.7. Actualización de datos personales

`#19` · Sprint 3 · 3 puntos · Resuelta

**Como** empleado,  
**Quiero** poder editar mi foto de perfil, teléfono de contacto y dirección,  
**Para** mantener a RRHH actualizado sin tener que enviarles correos.

**Criterios de aceptación**

- **CA01:** El formulario de edición para el empleado solo permite alterar campos de contacto.
- **CA02:** Los cambios realizados se reflejan inmediatamente en la base de datos general.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#117` BACK_Dirección y edición de datos de contacto | 2 | 2 | Cerrada |
| `#118` BACK_Foto de perfil en Supabase Storage | 4 | 4 | Cerrada |
| `#119` FRONT_Formulario de contacto y foto | 3 | 3 | Cerrada |
| `#120` QA_Pruebas de datos personales y foto | 2 | 2 | Cerrada |
| `#155` BACK_Compatibilidad del cliente de Storage con las llaves nuevas | 1 | 1 | Cerrada |

### HU 2.8. Certificado laboral descargable

`#163` · Sprint 5 · 3 puntos · Resuelta

**Como** empleado,  
**Quiero** descargar un certificado laboral con mi tipo de vinculación a la empresa,  
**Para** presentarlo en trámites (bancos, arriendos, visas) sin pedírselo a RR. HH.

**Criterios de aceptación**

- **CA01:** Desde "Mi perfil" descargo un PDF con el nombre de la empresa, mi nombre y documento, cargo, área, tipo de contrato, fecha de ingreso y fecha de expedición.
- **CA02:** Puedo elegir si incluye el salario.
- **CA03:** Solo un empleado activo con contrato vigente puede descargarlo, y siempre el suyo (sin id en la ruta).
- **CA04:** Cada certificado queda en la auditoría con un código de verificación impreso en el documento.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#177` BACK_Generación del certificado laboral en PDF | 3 | 3 | Cerrada |
| `#178` FRONT_Tarjeta de certificado laboral en Mi perfil | 1 | 1 | Cerrada |
| `#179` QA_Pruebas del certificado laboral | 2 | 2 | Cerrada |

### HU 3.1. Asignación de contrato (ingreso / reingreso)

`#22` · Sprint 3 · 3 puntos · Resuelta

**Como** administrador de RRHH,  
**Quiero** poder asignarle un tipo de contrato (Indefinido, Fijo, Prestación de Servicios) y fechas de vigencia a un empleado,  
**Para** formalizar su vinculación laboral en el sistema.

**Criterios de aceptación**

- **CA01:** El sistema debe permitir seleccionar el Tipo de Contrato desde una lista predefinida.
- **CA02:** Si el contrato es a "Término Fijo", la fecha de finalización es obligatoria.
- **CA03:** Si el contrato es "Indefinido", la fecha de finalización debe quedar vacía o deshabilitada.
- **CA04:** Si el empleado estaba Inactivo, al asignarle un nuevo contrato su estado pasa automáticamente a Activo (Reingreso).

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#121` BACK_Historial de contratos y tipo Prestación de Servicios | 3 | 3 | Cerrada |
| `#122` BACK_Asignación de contrato y reingreso | 3 | 3 | Cerrada |
| `#123` FRONT_Formulario de asignación de contrato | 3 | 3 | Cerrada |
| `#124` QA_Pruebas de asignación y reingreso | 2 | 2 | Cerrada |

### HU 3.2. Alertas de vencimiento próximo de contratos

`#23` · Sprint 3 · 3 puntos · Resuelta

**Como** gerente o coordinador de RRHH,  
**Quiero** que el sistema me notifique qué contratos a término fijo están por vencerse en los próximos 30 días,  
**Para** gestionar las renovaciones o terminaciones con el tiempo legal requerido.

**Criterios de aceptación**

- **CA01:** En el Dashboard principal debe existir una sección visible de "Contratos por vencer".
- **CA02:** El sistema calcula automáticamente la diferencia entre la fecha actual y la fecha fin del contrato.
- **CA03:** Solo muestra empleados cuyo estado sea "ACTIVO".
- **CA04:** Se muestra una tabla pequeña o widget con el nombre, los días restantes y el estado de los contratos que vencen en menos de 30 días (criterio incorporado desde la HU 6.2).

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#128` BACK_Endpoint de contratos por vencer | 2 | 2 | Cerrada |
| `#129` FRONT_Sección Contratos por vencer en el dashboard | 2 | 2 | Cerrada |
| `#130` QA_Pruebas de alertas de vencimiento | 1.5 | 1.5 | Cerrada |

### HU 3.3. Finalización de contrato

`#24` · Sprint 3 · 3 puntos · Resuelta

**Como** coordinador de recursos humanos,  
**Quiero** registrar la terminación del contrato de un empleado seleccionando su fecha de salida,  
**Para** mantener el historial de exempleados bloqueando su acceso al sistema, pero sin borrar su información.

**Criterios de aceptación**

- **CA01:** El sistema debe solicitar confirmación doble (ventana modal) antes de aplicar la baja.
- **CA02:** Se debe exigir una fecha de finalización válida (no puede ser anterior a la fecha de inicio del contrato).
- **CA03:** El estado del empleado cambia automáticamente a "INACTIVO" y su cuenta de usuario (login) se desactiva.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#125` BACK_Finalización de contrato y desactivación de la cuenta | 3 | 3 | Cerrada |
| `#126` FRONT_Modal de doble confirmación de baja | 2 | 2 | Cerrada |
| `#127` QA_Pruebas de finalización de contrato | 1.5 | 1.5 | Cerrada |
| `#156` BACK_Proteger al último administrador en la baja | 2 | 2 | Cerrada |

### HU 4.1. Solicitud de vacaciones (rol empleado)

`#27` · Sprint 4 · 5 puntos · Resuelta

**Como** empleado activo,  
**Quiero** poder solicitar un rango de días de vacaciones desde mi portal,  
**Para** notificar a RRHH de mis fechas de descanso planificadas.

**Criterios de aceptación**

- **CA01:** El empleado debe seleccionar fecha de inicio y fecha fin en un calendario.
- **CA02:** El sistema debe calcular cuántos días hábiles/laborables hay en ese rango (omitiendo fines de semana por defecto).
- **CA03:** No se permite enviar una solicitud que exceda el número de días disponibles del empleado.
- **CA04:** La solicitud queda en estado "PENDIENTE".

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#140` BACK_Endpoint de solicitud de vacaciones con validaciones | 5 | 5 | Cerrada |
| `#141` FRONT_Pantalla Mis vacaciones | 5 | 5 | Cerrada |
| `#142` QA_Pruebas de solicitud de vacaciones | 2.5 | 2.5 | Cerrada |

### HU 4.2. Aprobación o rechazo de vacaciones (talento humano)

`#28` · Sprint 4 · 3 puntos · Resuelta

**Como** administrador de recursos humanos,  
**Quiero** ver una bandeja de solicitudes de vacaciones pendientes para aprobarlas o rechazarlas,  
**Para** mantener el control operativo de la empresa.

**Criterios de aceptación**

- **CA01:** El Admin ve una tabla con todas las solicitudes PENDIENTES.
- **CA02:** Al "Aprobar", la solicitud pasa a estado APROBADA y el sistema descuenta los días del saldo del empleado.
- **CA03:** Al "Rechazar", la solicitud pasa a RECHAZADA (pidiendo un comentario obligatorio del motivo) y no se descuentan los días.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#143` BACK_Endpoints de aprobación y rechazo de vacaciones | 4 | 4 | Cerrada |
| `#144` FRONT_Bandeja de solicitudes pendientes | 4 | 4 | Cerrada |
| `#145` QA_Pruebas de aprobación y rechazo | 2 | 2 | Cerrada |
| `#157` BACK_Bandeja de vacaciones sin N+1 | 2 | 2 | Cerrada |

### HU 4.5. Cancelar mi solicitud de vacaciones

`#159` · Sprint 5 · 3 puntos · Resuelta

**Como** empleado,  
**Quiero** cancelar una solicitud de vacaciones pendiente, o aprobada que aún no empieza,  
**Para** corregir mis planes sin depender de RR. HH.

**Criterios de aceptación**

- **CA01:** El botón "Cancelar" aparece solo en mis solicitudes PENDIENTES, o APROBADAS con fecha de inicio futura.
- **CA02:** La solicitud pasa a CANCELADA y los días vuelven al saldo de inmediato.
- **CA03:** La cancelación queda en la auditoría (VACATION_CANCELLED).

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#165` BACK_Endpoint para cancelar mi solicitud de vacaciones | 2 | 2 | Cerrada |
| `#166` FRONT_Botón Cancelar en Mis vacaciones | 2 | 2 | Cerrada |
| `#167` QA_Pruebas de la cancelación | 2 | 2 | Cerrada |

### HU 4.7. Notificaciones de solicitudes de vacaciones

`#161` · Sprint 5 · 5 puntos · Resuelta

**Como** analista de RR. HH., quiero ver cuántas solicitudes pendientes hay; como empleado, quiero saber cuándo se decidió la mía,  
**Para** actuar a tiempo sin revisar las pantallas a cada rato.

**Criterios de aceptación**

- **CA01:** Un contador de pendientes junto a "Solicitudes de vacaciones" en la barra lateral (solo ADMIN y RR. HH.).
- **CA02:** En "Mis vacaciones", un aviso de las solicitudes decididas desde mi última visita, y una marca en la barra lateral mientras haya decisiones sin ver.
- **CA03 (fuera de alcance de este sprint):** correo transaccional con el proveedor configurado por variable de entorno.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#171` BACK_Contadores de solicitudes pendientes y decisiones sin ver | 3 | 3 | Cerrada |
| `#172` FRONT_Badges en la barra lateral y aviso en Mis vacaciones | 3 | 3 | Cerrada |
| `#173` QA_Pruebas de notificaciones | 2 | 2 | Cerrada |

### HU 4.3. Control de saldo de vacaciones automático

`#30` · Sprint 4 · 3 puntos · Resuelta

**Como** empleado y administrador,  
**Quiero** ver exactamente cuántos días de vacaciones disponibles tengo (o tiene un empleado),  
**Para** saber con cuánto tiempo libre cuento.

**Criterios de aceptación**

- **CA01:** El sistema debe calcular el saldo base (ej. 15 días por cada año trabajado).
- **CA02:** El saldo debe restarse matemáticamente basándose solo en las solicitudes APROBADAS.
- **CA03:** El número de días disponibles debe ser visible siempre en el perfil del empleado.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#137` BACK_Tabla vacation_requests y cálculo del saldo de vacaciones | 4 | 4 | Cerrada |
| `#138` FRONT_Saldo de vacaciones en Mi perfil y en el expediente | 2 | 2 | Cerrada |
| `#139` QA_Pruebas del saldo de vacaciones | 2 | 2 | Cerrada |

### HU 4.4. Calendario de ausencias

`#31` · Sprint 4 · 5 puntos · Resuelta

**Como** gerente o administrador,  
**Quiero** ver un calendario visual mensual con las vacaciones aprobadas de todo el personal,  
**Para** planificar operativamente y evitar que todo un equipo salga al mismo tiempo.

**Criterios de aceptación**

- **CA01:** Se muestra una vista de calendario tipo cuadrícula.
- **CA02:** Solo se muestran los días correspondientes a solicitudes APROBADAS.
- **CA03:** Al pasar el cursor sobre un día marcado, debe mostrar el nombre del empleado ausente.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#146` BACK_Endpoint de calendario de ausencias | 2 | 2 | Cerrada |
| `#147` FRONT_Calendario mensual de ausencias | 6 | 6 | Cerrada |
| `#148` QA_Pruebas del calendario de ausencias | 2 | 2 | Cerrada |
| `#185` FRONT_Calendario de ausencias con avatares y tarjetas | 4 | 4 | Cerrada |

### HU 4.6. Festivos de Colombia en el conteo de días

`#160` · Sprint 5 · 3 puntos · Resuelta

**Como** analista de RR. HH.,  
**Quiero** que los festivos de Colombia no cuenten como días de vacaciones,  
**Para** que el saldo descontado sea el legal.

**Criterios de aceptación**

- **CA01:** Tabla de festivos (fecha, nombre) administrable por ADMIN, con los festivos calculados del año en curso y el siguiente (fijos, Ley Emiliani y los que dependen de la Pascua).
- **CA02:** El conteo de días hábiles del servidor y su espejo en el formulario excluyen los festivos.
- **CA03:** El calendario de ausencias marca los festivos.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#168` BACK_Tabla de festivos y cálculo de festivos de Colombia | 4 | 4 | Cerrada |
| `#169` FRONT_Festivos en el formulario, el calendario y pantalla de administración | 3 | 3 | Cerrada |
| `#170` QA_Pruebas de festivos | 2 | 2 | Cerrada |

### HU 4.8. Calendario de ausencias filtrado por área

`#162` · Sprint 5 · 2 puntos · Resuelta

**Como** líder de equipo o analista de RR. HH.,  
**Quiero** filtrar el calendario de ausencias por área,  
**Para** evitar que todo un equipo salga al mismo tiempo.

**Criterios de aceptación**

- **CA01:** Un selector de área en el calendario; la consulta filtra por área en el servidor.
- **CA02:** Al elegir un día, el aviso "N personas de esta área ausentes".

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#174` BACK_Filtro por área en el calendario y lista de áreas | 1 | 1 | Cerrada |
| `#175` FRONT_Selector de área y aviso de ausentes por día | 2 | 2 | Cerrada |
| `#176` QA_Pruebas del calendario por área | 1 | 1 | Cerrada |

### HU 5.1. Log de actividad de usuarios

`#34` · Sprint 3 · 5 puntos · Resuelta

**Como** administrador del sistema,  
**Quiero** ver un registro automático de qué usuario modificó datos críticos (como el salario o el estado de un contrato),  
**Para** auditar posibles errores, fraudes o accesos no autorizados.

**Criterios de aceptación**

- **CA01:** El sistema registra en background: Quién hizo el cambio, Qué dato cambió, Cuándo lo hizo y la IP..
- **CA02:** Existe una vista de "Auditoría" exclusiva para el Admin donde se lista este historial ordenado por fecha.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#103` BACK_Tabla audit_logs (migración con RLS) y servicio de auditoría | 4 | 4 | Cerrada |
| `#104` BACK_Endpoint GET /audit paginado (solo ADMIN) | 2 | 2 | Cerrada |
| `#105` FRONT_Vista de Auditoría | 3 | 3 | Cerrada |
| `#106` QA_Pruebas de auditoría | 2 | 2 | Cerrada |

### HU 5.2. Exportar lista de empleados a excel/csv

`#36` · Sprint 4 · 2 puntos · Resuelta

**Como** analista de recursos humanos,  
**Quiero** poder descargar la tabla de empleados en formato Excel o CSV,  
**Para** cruzar datos con el sistema de nómina externo o contabilidad.

**Criterios de aceptación**

- **CA01:** La vista de lista de empleados debe tener un botón de "Exportar".
- **CA02:** El archivo exportado debe respetar los filtros que el usuario tenga activos en la pantalla

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#149` BACK_Exportación CSV de empleados con filtros | 3 | 3 | Cerrada |
| `#150` FRONT_Botón Exportar en el listado de empleados | 1.5 | 1.5 | Cerrada |
| `#151` QA_Pruebas de exportación | 1.5 | 1.5 | Cerrada |

### HU 5.3. Exportar la lista de empleados a Excel (.xlsx)

`#164` · Sprint 5 · 2 puntos · Nueva

**Como** analista de RR. HH.,  
**Quiero** descargar la lista de empleados como archivo de Excel real,  
**Para** abrirlo sin paso de importación y con los teléfonos, fechas y salarios en su tipo correcto.

**Criterios de aceptación**

- **CA01:** Un selector "CSV / Excel" junto a "Exportar".
- **CA02:** El .xlsx tiene las mismas columnas, filtros, reglas de salario por rol y auditoría que el CSV; ninguna celda se interpreta como fórmula.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#180` BACK_Exportación de empleados a .xlsx | 2 | — | Nueva |
| `#181` FRONT_Selector CSV / Excel en Exportar | 1 | — | Nueva |
| `#182` QA_Pruebas de la exportación .xlsx | 1 | — | Nueva |

### HU 6.1. Visualización de indicadores generales

`#39` · Sprint 2 · 2 puntos · Resuelta

**Como** gerente o líder de recursos humanos,  
**Quiero** ver tarjetas de resumen al entrar al sistema,  
**Para** conocer la salud demográfica de mi empresa en segundos.

**Criterios de aceptación**

- **CA01:** El dashboard debe mostrar: Total de Empleados Históricos, Total Activos, y Total Inactivos.
- **CA02:** Los números deben actualizarse dinámicamente según la base de datos, sin recargar la página.

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#94` BACK_Endpoint GET /employees/stats | 1 | 1 | Cerrada |
| `#95` FRONT_Tarjetas de indicadores en el dashboard | 2 | 2 | Cerrada |
| `#96` QA_Pruebas de indicadores | 1 | 1 | Cerrada |
| `#186` BACK_Aniversarios laborales y has_photo en listados | 2 | 2 | Cerrada |
| `#187` FRONT_Tarjeta de aniversarios y fotos en listados | 3 | 3 | Cerrada |

### HU 7.1. Pruebas automatizadas de autenticación y empleados

`#77` · Sin sprint · 3 puntos · Activa

**Como** equipo de desarrollo  
**Quiero** pruebas automatizadas de los flujos críticos  
**Para** detectar errores antes de integrar cambios y no depender de pruebas manuales

**Criterios de aceptación**

- **CA01:** Las pruebas corren con un solo comando (pytest) y usan una base de datos de pruebas separada; nunca tocan la base de datos real
- **CA02:** Cada prueba es independiente (la base de datos queda limpia entre pruebas)
- **CA03:** Cubren login (éxito, credenciales incorrectas, acceso sin sesión con 401) y logout (el token anterior queda revocado)
- **CA04:** Cubren el registro de empleado (201, documento duplicado 409, correo duplicado 409, reingreso tras INACTIVO 201, datos inválidos 422, sin sesión 401)

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#54` QA_Pruebas de autenticación (login y logout) | 2 | 2 | Cerrada |
| `#66` QA_Pruebas de registro de empleado | 2 | 2 | Cerrada |
| `#80` QA_Configurar entorno de pruebas (BD de pruebas, conftest, fixtures) | 3 | 3 | Cerrada |
| `#152` QA_Configurar Playwright y job E2E en el CI | 5 | 5 | Cerrada |
| `#153` QA_Pruebas E2E de los flujos del Sprint 3 | 5 | 5 | Cerrada |

### HU 7.2. Despliegue (Render y Vercel) e integración continua

`#79` · Sprint 3 · 3 puntos · Activa

**Como** equipo de desarrollo  
**Quiero** desplegar la API y el frontend con una integración continua que valide cada cambio  
**Para** detectar a tiempo problemas de entorno (cookies, CORS) y entregar siempre una versión funcional

**Criterios de aceptación**

- **CA01:** La API queda publicada en Render y el frontend en Vercel, con el rewrite /api/* hacia la API para que el navegador vea un solo origen
- **CA02:** El login funciona en producción con la cookie HttpOnly (SameSite=Lax y Secure)
- **CA03:** Cada pull request ejecuta las verificaciones automáticas (lint, tipos y pruebas) y el merge a main exige que pasen

| Tarea | Estimado (h) | Real (h) | Estado |
|---|:-:|:-:|---|
| `#97` QA_Crear BD de pruebas separada (tat-test) antes del despliegue | 1 | — | Nueva |
| `#98` BACK_Endurecer configuración de producción (cookie Secure, /docs, no-store) | 2 | 2 | Cerrada |
| `#99` BACK_Rate limiting en login y logging sin secretos | 3 | 3 | Cerrada |
| `#100` QA_Integración continua con GitHub Actions | 3 | 3 | Cerrada |
| `#101` BACK_Preparar archivos y guía de despliegue | 3 | 3 | Cerrada |
| `#102` OPS_Publicar en Render y Vercel y validar login en producción | 2 | 2 | Cerrada |
| `#154` BACK_Actualizar dependencias con vulnerabilidades | 1.5 | 1.5 | Cerrada |
| `#158` BACK_Configurar despliegue continuo (región, checks, previews) | 1 | 1 | Cerrada |
| `#189` QA_Documentación de entrega: README, arquitectura y manual de usuario | 4 | 4 | Cerrada |
| `#190` QA_Documento de gestión del proyecto: backlog, historias, tareas y horas | 3 | 3 | Cerrada |

## 5. Tareas sin historia asociada

Mejoras de calidad visual y de experiencia hechas al cierre del proyecto.

| Tarea | Sprint | Estimado (h) | Real (h) | Estado |
|---|---|:-:|:-:|---|
| `#183` FRONT_Ajustes visuales y responsive | Sprint 5 | 14 | 14 | Cerrada |
| `#184` FRONT_Correcciones de la segunda revisión visual | Sprint 5 | 4 | 4 | Cerrada |
| `#188` FRONT_Avisos emergentes y esqueletos de carga | Sprint 5 | 4 | 4 | Cerrada |
