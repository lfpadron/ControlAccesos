# Notas de Seguridad

## Decisiones iniciales

- HTTPS es obligatorio en producción. Caddy queda como punto natural para terminar TLS o integrarse con un balanceador.
- Las contraseñas se almacenan con Argon2id mediante `argon2-cffi`.
- JWT se usa como mecanismo temporal de sesión para desarrollo inicial.
- RBAC queda preparado con roles base y dependencia extensible. La validación fina por institución/complejo sigue pendiente.
- La auditoría es obligatoria para cambios operativos relevantes y registra creación, edición, activación y desactivación de catálogos operativos.
- Las pantallas públicas solo deben exponer turno y consultorio; no deben mostrar paciente, médico, especialidad ni hora de cita.
- Los QR se firman con secreto del servidor y la base solo guarda `token_hash`; no se persiste el token plano.
- El payload lógico del QR contiene `cita_id`, `folio_turno`, emisión, expiración y firma. No contiene paciente, médico, consultorio, especialidad ni información clínica.
- La búsqueda pública de kiosko/PWA devuelve datos mínimos: turno, hora, consultorio, piso y estado.
- No se deben guardar datos clínicos en esta base inicial.
- No se deben registrar secretos, tokens, contraseñas ni datos sensibles en logs.

## Pendientes antes de producción

- Rotación y custodia formal de secretos.
- Política de expiración y refresh tokens.
- RBAC granular por institución, complejo, rol y permiso.
- 2FA real para usuarios administrativos.
- Cifrado en reposo para base de datos, backups y configuraciones sensibles.
- Hardening de CORS, headers y políticas de sesión.
- Auditoría completa de login y acciones de operadores.
- Backups cifrados y pruebas de restauración.

## Alcance de datos

La plataforma debe operar control de acceso y flujo administrativo. Los módulos futuros deben evitar guardar información clínica salvo que exista una decisión legal, técnica y de seguridad específica para hacerlo.
