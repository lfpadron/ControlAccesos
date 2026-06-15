# Flujo Operativo v01

## Paciente con QR

1. Recepción u operador crea paciente.
2. Se crea cita programada o espontánea.
3. El sistema genera `folio_turno` y QR firmado.
4. El ticket lógico puede renderizarse con turno, QR, consultorio, piso y hora.
5. El paciente llega al kiosko o PWA y pega el token QR.
6. El sistema valida firma, expiración y ventana temporal.
7. Si procede, registra `CHECKIN_LOBBY` y cambia cita a `LLEGO_LOBBY`.

## Paciente busca por nombre

1. El paciente elige `Buscar por nombre`.
2. Kiosko consulta `/api/citas/buscar` para citas de hoy.
3. Solo se muestran turno, hora, consultorio, piso y estado.
4. El paciente selecciona su cita.
5. Se registra llegada con canal `KIOSKO`.

## Operador crea cita espontánea

1. Operador crea o busca paciente.
2. Crea cita con tipo `ESPONTANEA`.
3. El sistema genera folio corto no secuencial.
4. Puede generar QR o registrar llegada directamente.

## Paciente llega

La llegada devuelve:

- `VERDE`: dentro de 120 minutos antes y 30 minutos después.
- `AMARILLO`: válida, pero entre 240 y 120 minutos antes.
- `ROJO`: QR inválido, cita cancelada, expirada o fuera de ventana.

## Operador llama paciente

1. En `Citas de hoy`, operador usa `Llamar`.
2. Backend crea `turnos_display` y registra `TURNO_LLAMADO` o `TURNO_RELLAMADO`.
3. La pantalla pública obtiene turnos por polling.
4. El turno aparece resaltado y luego pasa a estilo normal hasta ocultarse.
