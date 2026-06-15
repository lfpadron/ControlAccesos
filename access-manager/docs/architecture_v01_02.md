# Arquitectura v01.02

Resumen de la iteración de flujo operativo:

```text
FastAPI + PostgreSQL + Redis + Vue/Vite + Kiosko + PWA + Display + Print Agent + Podman
```

## Cambios

- Se agrega dominio de pacientes y citas reales.
- La cita reemplaza el turno técnico previo con `folio_turno` único por complejo y fecha.
- El QR firmado se genera desde backend y se almacena solo como hash.
- Kiosko y PWA consumen endpoints públicos mínimos para buscar cita de hoy y registrar llegada.
- La web administrativa concentra creación de pacientes, citas y operación diaria.
- El display público conserva privacidad: solo turno y consultorio.

## Contrato de privacidad

Los módulos públicos no muestran datos clínicos ni personales innecesarios. El display no muestra paciente. El QR no contiene paciente, médico, consultorio, especialidad ni notas.
