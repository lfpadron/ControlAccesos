# Desarrollo Local

## Preparar entorno

```bash
cd access-manager
cp .env.example .env
```

Edita `.env` y cambia al menos:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET`
- `QR_SIGNING_SECRET`
- `SEED_ADMIN_PASSWORD`

El backend administra dependencias con `uv`. Para preparar el entorno local de Python:

```bash
cd backend
uv sync
```

## Levantar servicios

Con Podman:

```bash
podman compose up --build
```

Con Docker:

```bash
docker compose up --build
```

## Migrar base de datos

```bash
podman compose exec backend uv run alembic upgrade head
```

## Crear administradores semilla

```bash
podman compose exec backend uv run python -m app.services.seed_admins
```

## Desarrollo del backend

La API vive en `backend/app`. Para nuevas tablas:

1. Crear modelo SQLAlchemy.
2. Crear schemas Pydantic.
3. Agregar router o servicio.
4. Generar migración Alembic.
5. Revisar que no se registren secretos ni datos sensibles en logs.

Comando útil:

```bash
podman compose exec backend uv run alembic revision --autogenerate -m "descripción"
```

## Desarrollo frontend

Cada app Vue/Vite es independiente:

- `frontend`: administración.
- `kiosk`: kiosko.
- `mobile-pwa`: PWA móvil.

Se publican por Caddy en:

- `/`
- `/kiosk/`
- `/mobile/`
- `/display/demo-lobby`

## Flujo demo rápido

1. Inicia sesión en `http://localhost:8080` con `admin1@example.com` y la contraseña de `SEED_ADMIN_PASSWORD`.
2. Abre `Citas de hoy`.
3. Genera QR o ticket lógico para la cita demo.
4. Abre `http://localhost:8080/kiosk/` y busca `Paciente Demo`, o pega el token QR.
5. Registra llegada.
6. En `Citas de hoy`, usa `Llamar`.
7. Abre `http://localhost:8080/display/demo-lobby` para ver el turno llamado.

Mantener el cliente API centralizado en `frontend/src/api/client.ts` para evitar duplicar manejo de token y errores. Las pantallas nuevas de catálogos usan `frontend/src/catalogs.ts` para definir campos, columnas y endpoints.

## Pruebas y validación

Backend:

```bash
podman compose exec backend uv run pytest -q
```

Frontend web:

```bash
cd frontend
npm run build
```

Kiosko:

```bash
cd kiosk
npm run build
```

Mobile PWA:

```bash
cd mobile-pwa
npm run build
```

Smoke test por Caddy:

```bash
curl http://localhost:8080/api/health
```

## Limpieza local

Para detener:

```bash
podman compose down
```

Para eliminar volúmenes locales de datos:

```bash
podman compose down -v
```

Usa la eliminación de volúmenes solo cuando quieras borrar la base de datos local.
