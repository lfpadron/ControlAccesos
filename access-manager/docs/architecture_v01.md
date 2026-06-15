# Arquitectura v01

Access Manager arranca como un monorepo con servicios separados y contratos simples:

```text
FastAPI + PostgreSQL + Redis + Vue/Vite + PWA + Print Agent + Podman
```

## Componentes

- `backend`: API FastAPI con autenticación, healthchecks, modelos iniciales, migraciones Alembic y auditoría base.
- `worker`: proceso Python preparado para notificaciones, impresión y tareas programadas futuras usando Redis.
- `postgres`: base relacional principal con volumen persistente.
- `redis`: cola/cache operativa para trabajos asíncronos.
- `frontend`: web administrativa para instituciones, complejos y catálogos operativos.
- `kiosk`: app web separada para recepción/autoservicio.
- `mobile-pwa`: PWA mínima para flujos móviles.
- `display`: vista web pública para pantallas de turnos, servida por el frontend en `/display/{codigo}`.
- `print-agent`: estructura del agente local cercano a impresoras.
- `caddy`: punto de entrada HTTP para API y frontends.

## Principios tomados de la arquitectura tecnológica

- Estabilidad antes que amplitud funcional.
- Seguridad de información desde el primer commit.
- Portabilidad entre entorno local, nube y despliegue on-premise.
- Interfaz minimalista y rápida.
- Separación entre administración, kiosko, móvil y agentes locales.

## Flujo de entrada

```text
Usuario / Kiosko / PWA
  -> Caddy
  -> Frontend estático o API FastAPI
  -> PostgreSQL para datos persistentes
  -> Redis para trabajos futuros
  -> Worker / Print Agent en iteraciones posteriores
```

## Capa operativa v0.3.0

La versión `0.3.0` agrega el flujo operativo central:

- Roles y asignación de roles por usuario.
- Usuarios administrativos y operativos.
- Pisos, salas de espera y consultorios por complejo.
- Médicos y operadores.
- Asignaciones médico-consultorio y operador-destino.
- Pantallas de turnos con polling configurable, estilos de resaltado y ocultamiento por tiempo.
- Pacientes con folio operativo corto.
- Citas programadas y espontáneas con folio de turno de 4 caracteres.
- QR firmado por servidor, con hash persistido y sin datos personales en el payload.
- Ticket lógico para impresión futura.
- Check-in de lobby y sala.
- Kiosko y PWA con búsqueda, QR manual y registro de llegada.
- Auditoría automática de cambios administrativos.

## Flujo v01

```text
Paciente
  -> Cita
  -> QR firmado / Ticket lógico
  -> Check-in de llegada
  -> Operador o médico llama al turno
  -> Pantalla pública muestra turno y consultorio
```

## Módulos futuros

La estructura queda preparada para agregar impresión física, cámara QR real, notificaciones, reportes, respaldos cifrados y permisos granulares sin mezclar esas responsabilidades en el flujo v01.
