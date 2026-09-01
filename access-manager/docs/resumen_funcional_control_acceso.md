# Resumen funcional de Control de Acceso

## Resumen ejecutivo

Control de Acceso es una plataforma para administrar la operación diaria de llegada, validación, orientación y llamado de pacientes en edificios médicos, clínicas, hospitales, torres de consultorios o campus multiinstitución.

El sistema organiza el flujo desde la creación de pacientes y citas hasta el check-in, la autorización para pasar, el llamado en pantallas públicas y el cierre operativo de la atención. Su diseño prioriza la trazabilidad, la seguridad de la información, la configuración por ubicación física y la reducción de tareas manuales en recepción.

La solución integra portal web administrativo, kioskos de autoservicio, pantallas públicas de turnos, app móvil Android para recepción, app móvil para médicos, PWA móvil y una API central que concentra reglas de negocio, permisos y auditoría.

## Objetivo funcional

El objetivo principal es controlar de forma ordenada el acceso de pacientes a consultorios y áreas de atención, evitando filas innecesarias, llamadas manuales, duplicidad de capturas y exposición de datos personales en zonas públicas.

El sistema permite:

- Registrar pacientes y asociarlos con médicos.
- Crear citas programadas o espontáneas.
- Generar folios cortos de turno y códigos QR firmados.
- Registrar llegada por QR, kiosko, recepción o app móvil.
- Consultar y operar las citas del día.
- Autorizar el paso de pacientes.
- Llamar turnos hacia pantallas públicas.
- Administrar usuarios, roles, permisos y alcances por ubicación.
- Consultar auditoría y reportes operativos.

## Usuarios principales

| Usuario | Uso funcional |
| --- | --- |
| Administrador del sistema | Configura instituciones, usuarios, roles, permisos y catálogos base. |
| Administrador de negocio u operación | Administra campus, torres, pisos, consultorios, pantallas, kioskos y reglas operativas. |
| Recepción | Registra llegadas, busca citas, valida QR, opera check-in y consulta citas del día. |
| Médico | Consulta agenda, pacientes asociados, estado de llegada y puede llamar pacientes. |
| Operador | Apoya la operación de citas, turnos, consultorios o médicos asignados. |
| Paciente | Realiza check-in en kiosko o mediante QR sin acceder a información administrativa. |
| Seguridad o control de accesos | Apoya validación de llegada y orientación del paciente. |

## Flujo operativo principal

```text
Paciente
  -> Registro o búsqueda
  -> Cita programada o espontánea
  -> Folio de turno y QR firmado
  -> Llegada por kiosko, recepción, QR o app móvil
  -> Check-in de lobby
  -> Autorización para pasar
  -> Llamado de turno
  -> Pantalla pública muestra turno y destino
  -> Consulta, cierre, cancelación o no presentación
```

## Estados funcionales de una cita

| Estado | Significado operativo |
| --- | --- |
| `AGENDADA` | La cita existe y está pendiente de llegada. |
| `QR_GENERADO` | La cita cuenta con QR activo o emitido. |
| `LLEGO_LOBBY` | El paciente registró llegada en lobby o punto de acceso. |
| `AUTORIZADO_PASAR` | El paciente fue autorizado para avanzar al área de atención. |
| `EN_CONSULTA` | La atención médica está en curso. |
| `FINALIZADA` | La cita concluyó. |
| `NO_LLEGO` | El paciente no se presentó o no respondió al llamado. |
| `CANCELADA` | La cita fue cancelada manualmente o por regla operativa. |
| `EXPIRADA` | La cita o su QR quedaron fuera de vigencia. |

## Módulos funcionales

### 1. Administración institucional

Controla la estructura organizacional sobre la que opera el sistema:

- Instituciones.
- Campus o complejos.
- Torres.
- Pisos.
- Salas de espera.
- Consultorios.
- Clústers de turnos.

Estos catálogos permiten modelar edificios médicos de una o varias sedes, ubicar físicamente cada consultorio y definir qué pantallas o kioskos atienden cada zona.

### 2. Usuarios, roles y permisos

Administra cuentas de acceso y privilegios:

- Alta y edición de usuarios.
- Contraseñas temporales y cambio obligatorio de contraseña.
- Roles configurables.
- Permisos por pantalla con niveles `sin acceso`, `consultar` y `editar`.
- Pantalla inicial configurable por rol.
- Asignación de usuarios por institución, campus, torre, piso, consultorio o médico.
- Vigencias de asignación para limitar accesos por fecha.

El modelo permite separar funciones administrativas, operativas, médicas y de recepción.

### 3. Médicos, operadores y asignaciones

Permite organizar quién atiende, dónde atiende y quién apoya la operación:

- Directorio operativo de médicos.
- Asociación opcional de médicos con usuarios del sistema.
- Preferencias de visualización del llamado de turnos.
- Estado del médico: disponible, en consulta, no disponible, ausente o no mostrar.
- Directorio de operadores.
- Asignación médico-consultorio con vigencia, horarios y días.
- Asignación de operadores a médicos o consultorios.

Este módulo ayuda a mantener actualizada la relación entre agenda, consultorios, pantallas y personal responsable.

### 4. Pacientes

Gestiona identidad operativa mínima del paciente:

- Alta de pacientes por médico.
- Búsqueda por nombre, celular o folio.
- Nombre preferido, apellidos, celular y fecha de nacimiento.
- Folio operativo de paciente.
- Activación, desactivación y marcado para borrado.

El sistema no funciona como expediente clínico. Los datos se limitan a lo necesario para operar citas, identificación y llegada.

### 5. Citas

Gestiona la agenda y la atención operativa:

- Citas programadas.
- Citas espontáneas.
- Médico, paciente, campus, piso, consultorio, fecha y hora.
- Duración estimada y notas operativas.
- Folio corto de turno generado automáticamente.
- Detección de posibles duplicados con confirmación.
- Cancelación, autorización, inicio y finalización de atención.

Las citas son el eje del flujo de acceso, ya que conectan paciente, médico, ubicación, QR, llegada y llamado.

### 6. Citas de hoy y recepción

Concentra la operación diaria:

- Tablero de citas del día.
- Filtros por fecha, horario, estado, institución, campus, torre, piso, consultorio, médico y paciente.
- Check-in manual desde recepción.
- Validación por QR desde lector físico o captura manual.
- Cancelación de check-in cuando la regla operativa lo permite.
- Autorización para pasar.
- Llamado o rellamado del turno.
- Registro de no llegada según reglas de llamado.

Este módulo está pensado para uso frecuente por recepción y operación durante la jornada.

### 7. QR y ticket lógico

El sistema emite QR firmados para validar la cita sin revelar datos sensibles:

- Generación de QR por cita.
- Validación de firma, vigencia y ventana temporal.
- Hash del token almacenado en servidor.
- Cancelación de QR.
- Check-in por QR desde recepción, kiosko, PWA o app móvil.
- Ticket lógico con turno, QR, fecha, hora, torre, piso y consultorio.

El QR no contiene nombre del paciente, médico, especialidad, consultorio ni información clínica.

### 8. Kioskos de autoservicio

Permiten que el paciente registre su llegada sin intervención directa de recepción:

- Configuración de puntos de acceso.
- Registro de kioskos por código de dispositivo y token.
- Asociación del kiosko a campus, torre o piso.
- Personalización visual de colores.
- Búsqueda de cita por nombre.
- Confirmación adicional por celular o fecha de nacimiento cuando hay homónimos.
- Check-in por cita encontrada.
- Check-in por QR.

El kiosko solo muestra información mínima para confirmar la cita: turno, hora, consultorio, piso y estado.

### 9. Pantallas públicas de turnos

Muestran llamados en salas o áreas comunes:

- Configuración de pantallas por dispositivo.
- Alcance por campus, piso, clúster o consultorio.
- Asociación de pantallas a clústers de turnos.
- Polling configurable.
- Tiempo de resaltado de turno nuevo.
- Tiempo de permanencia visible.
- Número máximo de turnos en pantalla.
- Configuración de colores y tamaños.
- Vista pública por código de dispositivo.
- Anuncio por voz en navegadores compatibles.

Las pantallas públicas están diseñadas para mostrar turno y destino, evitando datos personales o clínicos.

### 10. Clústers de turnos

Agrupan consultorios o zonas para controlar qué turnos se muestran en cada pantalla:

- Alta y edición de clústers.
- Asociación de consultorios a clústers.
- Consulta por piso o consultorio.
- Consulta de relación entre clústers y pantallas.
- Soporte para pantallas que muestran turnos, próxima cita o ambos.

Este módulo es útil cuando un piso tiene varias salas de espera o cuando distintas pantallas deben mostrar subconjuntos de consultorios.

### 11. Aplicaciones móviles

#### App Android de llegada

Dirigida a recepción o personal operativo:

- Login con usuario autorizado.
- Sesión local con expiración.
- Escaneo de QR con cámara.
- Búsqueda manual por nombre y dato de confirmación.
- Check-in contra servidor.
- Ticket PDF.
- Bitácora local sin datos personales del paciente.

#### App Android de médicos

Dirigida a médicos y asistentes:

- Login contra la API.
- Consulta de agenda por fecha, médico, paciente, estado y tipo.
- Consulta de pacientes accesibles.
- Creación de citas programadas o espontáneas.
- Cancelación de citas.
- Generación y visualización de QR.
- Llamado de pacientes.
- Refresco periódico para ver llegada registrada por recepción.

#### Mobile PWA

Alternativa ligera desde navegador:

- Consulta del estado de API.
- Escaneo o captura de QR.
- Búsqueda de paciente/cita.
- Creación de cita espontánea.
- Registro de llegada.

### 12. Reportes y auditoría

El sistema incluye herramientas de supervisión:

- Reportes generales de instituciones, campus, pisos, consultorios, salas, clústers y pantallas.
- Reportes médicos de pacientes y citas.
- Reportes de recepción agrupados por periodo, ubicación y horario.
- Exportación de resultados a formatos operativos como Excel, CSV o JSON.
- Bitácora de auditoría de cambios administrativos y eventos relevantes.

La auditoría registra usuario responsable, fecha, evento, entidad afectada, canal, IP y valores antes o después cuando aplica.

## Reglas operativas relevantes

- No se usa borrado físico desde la API para catálogos operativos; se activa o desactiva.
- Un consultorio no puede repetir código dentro del mismo campus.
- Salas y consultorios deben pertenecer a pisos válidos del mismo campus.
- Las fechas de fin no pueden ser anteriores a las fechas de inicio.
- El folio de turno es corto, no secuencial y único por campus y fecha.
- La detección de duplicados advierte, pero permite confirmación explícita.
- El check-in por QR valida firma, expiración y ventana temporal.
- Los llamados generan registros para pantallas públicas y pueden incrementarse como rellamados.
- Las pantallas públicas limitan la información visible al mínimo operativo.

## Seguridad y privacidad

Control de Acceso contempla medidas funcionales para reducir exposición de información:

- Autenticación por correo y contraseña.
- Tokens de sesión para API.
- Roles y permisos por pantalla.
- Alcance por institución, campus, torre, piso, consultorio o médico.
- QR firmado por servidor.
- Almacenamiento de hash del token QR.
- Auditoría de cambios y acciones relevantes.
- Datos mínimos en kioskos y pantallas públicas.
- Logs móviles sin datos personales del paciente.

## Plataformas incluidas

| Plataforma | Propósito |
| --- | --- |
| Web administrativa | Configuración, catálogos, seguridad, citas, recepción, reportes y auditoría. |
| Kiosko web | Autoservicio de pacientes en puntos físicos de acceso. |
| Pantalla pública | Visualización de turnos llamados en salas o áreas comunes. |
| Mobile PWA | Flujo móvil ligero desde navegador. |
| App Android de llegada | Registro móvil de llegada por QR o búsqueda. |
| App Android de médicos | Agenda, pacientes, QR y llamado desde perfil médico. |
| API central | Reglas de negocio, persistencia, seguridad, QR, auditoría y reportes. |

## Beneficios esperados

- Reduce filas y saturación en recepción.
- Estandariza el registro de llegada.
- Mejora la orientación del paciente hacia piso y consultorio.
- Disminuye errores en pacientes con nombres similares.
- Evita exponer datos personales en pantallas públicas.
- Da visibilidad a médicos y operadores sobre llegadas y estados.
- Facilita supervisión mediante reportes y auditoría.
- Permite operar en escenarios multiinstitución y multisede.

## Alcance actual

El alcance actual cubre administración institucional, usuarios, roles, pacientes, médicos, citas, check-in, QR, kioskos, pantallas de turnos, clústers, apps móviles, reportes y auditoría.

Quedan fuera del alcance funcional actual:

- Expediente clínico.
- Facturación y pagos.
- Mensajería masiva por WhatsApp, SMS o Telegram.
- Integraciones clínicas externas.
- Impresión física directa desde servidor.
- 2FA real.

La arquitectura permite evolucionar hacia esas integraciones sin mezclar el flujo de control de acceso con información clínica o financiera.
