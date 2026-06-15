# Access Manager

Access Manager es una base técnica para un sistema multiinstitución de gestión de accesos a torres de consultorios médicos. Este primer entregable prioriza estabilidad, seguridad inicial, portabilidad local/nube y una estructura clara para crecer hacia QR, citas, pantallas de sala, notificaciones e impresión.

La versión `0.3.0` agrega el flujo operativo central v01: pacientes, citas programadas y espontáneas, folio corto de turno, QR firmado, ticket lógico, check-in, kiosko funcional, PWA móvil básica y auditoría del flujo.

## Stack

- Backend API: Python 3.12, uv, FastAPI, SQLAlchemy 2.x, Alembic.
- Datos: PostgreSQL y Redis.
- Frontends: Vue 3, Vite y TypeScript.
- Infraestructura local: Podman Compose, compatible con Docker Compose.
- Proxy: Caddy.

## Arranque con Podman

```bash
cd access-manager
copy .env.example .env
podman compose up --build
```

En PowerShell también puedes usar:

```powershell
Copy-Item .env.example .env
podman compose up --build
```

El backend usa `uv` como manejador de paquetes de Python. Para trabajo local fuera del contenedor:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Arranque con Docker

```bash
cd access-manager
cp .env.example .env
docker compose up --build
```

## Migraciones

Con los servicios levantados:

```bash
podman compose exec backend uv run alembic upgrade head
```

Equivalente con Docker:

```bash
docker compose exec backend uv run alembic upgrade head
```

## Seeds

Configura `SEED_ADMIN_PASSWORD` en `.env` y ejecuta:

```bash
podman compose exec backend uv run python -m app.services.seed_admins
```

Se crean, si no existen:

- `admin1@example.com`
- `admin2@example.com`

También se crean roles base (`ADMIN_SISTEMA`, `ADMIN_NEGOCIO`, `RECEPCIONISTA`, `MEDICO`, `OPERADOR`, `GUARDIA_CONTINGENCIA`, `USUARIO_KIOSKO`), paciente demo, citas demo, pantalla demo y un QR activo. Usa la contraseña temporal definida por `SEED_ADMIN_PASSWORD` y cámbiala antes de cualquier despliegue real.

## URLs locales

- Web administrativa: [http://localhost:8080](http://localhost:8080)
- Kiosko: [http://localhost:8080/kiosk/](http://localhost:8080/kiosk/)
- Mobile PWA: [http://localhost:8080/mobile/](http://localhost:8080/mobile/)
- Display demo: [http://localhost:8080/display/demo-lobby](http://localhost:8080/display/demo-lobby)
- API health: [http://localhost:8080/api/health](http://localhost:8080/api/health)
- API docs: [http://localhost:8080/api/docs](http://localhost:8080/api/docs)

## TUI de control

En Windows puedes abrir una TUI para controlar el entorno local:

```powershell
.\control_tui.bat
```

La TUI se ejecuta con `uv run --with textual` y permite arrancar Podman, construir imágenes, encender el stack local, abrir el navegador en `http://localhost:8080/`, apagar servicios y revisar logs de comandos.

## Endpoints iniciales

- `GET /health`
- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/instituciones`
- `POST /api/instituciones`
- `GET /api/complejos`
- `POST /api/complejos`

## Endpoints operativos v0.2.0

Todos requieren token Bearer con rol administrativo:

- `/api/roles`
- `/api/usuarios`
- `/api/usuario-roles`
- `/api/pisos`
- `/api/salas-espera`
- `/api/consultorios`
- `/api/medicos`
- `/api/operadores`
- `/api/asignaciones-medico-consultorio`
- `/api/asignaciones-operador`
- `/api/pantallas-turnos`
- `/api/public-display/{codigo_dispositivo}/turnos`
- `/api/turnos-display/recientes`
- `/api/citas/{cita_id}/llamar`
- `/api/auditoria`

Los catálogos operativos soportan listar, consultar por ID, crear, actualizar, activar y desactivar. No se implementa borrado físico.

Las pantallas públicas muestran únicamente turno y consultorio. No exponen paciente, médico, especialidad ni hora de cita.

## Flujo operativo v01

Endpoints principales:

- `/api/pacientes`: alta, edición, activación, desactivación y búsqueda.
- `/api/citas`: citas programadas y espontáneas con folio corto no secuencial.
- `/api/citas/hoy`: tablero operativo diario.
- `/api/citas/buscar`: búsqueda pública mínima para kiosko/PWA.
- `/api/citas/{cita_id}/qr`: generación y consulta de QR firmado.
- `/api/qr/validar`: validación lógica de QR.
- `/api/qr/checkin`: check-in desde QR.
- `/api/citas/{cita_id}/ticket`: ticket lógico para renderizar o imprimir después.
- `/api/citas/{cita_id}/checkin-lobby`: llegada por búsqueda.
- `/api/citas/{cita_id}/llamar`: llamado a pantalla de turnos.

El QR no contiene paciente, médico, consultorio, especialidad ni información clínica. Se firma con `QR_SIGNING_SECRET` y solo se guarda el hash del token.

Los endpoints de instituciones y complejos requieren token Bearer. Para obtenerlo, ejecuta migraciones, crea seeds e inicia sesión con uno de los administradores semilla.

## Pruebas

Con servicios levantados y migraciones aplicadas:

```bash
podman compose exec backend uv run pytest -q
```

También se validan builds de frontend, kiosko y PWA con:

```bash
npm run build
```

## Estado del entregable

Incluye la base técnica, la capa operativa inicial y el flujo Paciente -> Cita -> QR -> Llegada -> Llamado -> Pantalla. No implementa todavía impresión física real, WhatsApp, Telegram, SMS, expediente clínico, facturación ni pagos.
