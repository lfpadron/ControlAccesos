# Dominio Operativo v0.3.0

Esta capa agrega catálogos, asignaciones y el flujo operativo central para controlar llegada y llamado de pacientes sin incluir datos clínicos.

## Entidades

- `roles`: catálogo de roles base del sistema.
- `usuario_roles`: asignación de roles a usuarios, opcionalmente por institución y complejo.
- `usuarios`: cuentas de acceso con contraseña hasheada y estado operativo.
- `pisos`: niveles físicos dentro de un complejo.
- `salas_espera`: áreas de espera ubicadas en un piso.
- `consultorios`: espacios físicos identificados por código único dentro de un complejo.
- `medicos`: directorio operativo de médicos, opcionalmente ligado a usuario.
- `operadores`: usuarios que ejecutan apoyo operativo.
- `asignaciones_medico_consultorio`: vigencia de uso de consultorio por médico.
- `asignaciones_operador`: asignación de operador a médico o consultorio dentro de un complejo.
- `pantallas_turnos`: configuración visual, polling y alcance físico de pantallas públicas.
- `turnos_display`: turnos llamados para mostrar en pantalla y consultar desde operación.
- `pacientes`: identidad operativa mínima para buscar y asociar citas.
- `citas`: agenda programada o espontánea con folio corto de turno.
- `qr_tokens`: QR firmado por servidor; solo se guarda hash del token.
- `eventos_llegada`: check-in de lobby o sala, con canal y dispositivo.
- `auditoria`: bitácora de cambios administrativos.

## Reglas Iniciales

- No hay borrado físico desde API; se usa activar/desactivar.
- Un consultorio no puede repetir `codigo` dentro del mismo complejo.
- Una sala o consultorio debe pertenecer a un piso del mismo complejo.
- Una asignación de operador debe indicar médico o consultorio.
- Las fechas de fin no pueden ser anteriores a las fechas de inicio.
- Los cambios administrativos generan eventos de auditoría.
- Las pantallas hacen polling ligero entre 2 y 10 segundos, con default de 5 segundos.
- Las pantallas públicas solo muestran turno y consultorio.
- Los turnos llamados se resaltan durante `segundos_resaltado` y se ocultan después de `segundos_visible`.
- Los turnos se ordenan por `llamado_en desc` y se limitan por `max_turnos_visibles`.
- Los pacientes requieren nombre, apellido paterno y al menos celular o fecha de nacimiento.
- Las citas generan `folio_turno` de 4 caracteres con alfabeto no ambiguo.
- El folio de turno es único por complejo y fecha.
- La detección de posible duplicado no bloquea permanentemente; requiere confirmación explícita.
- El QR firmado no contiene datos personales ni clínicos.
- La llegada por QR devuelve estado verde, amarillo o rojo según ventana temporal y validez.
- El ticket lógico contiene fecha, leyenda, turno, QR, consultorio, piso y hora.

## Fuera de Alcance

- Impresión real.
- 2FA real.
- Integraciones Telegram, WhatsApp o SMS.
- Expediente clínico.
- Facturación y pagos.
