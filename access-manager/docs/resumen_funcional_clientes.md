# Resumen funcional del sistema de control de accesos

## Resumen ejecutivo

El sistema de control de accesos centraliza la operación diaria de recepción, registro de llegada, atención de pacientes y llamado de turnos en edificios médicos, clínicas, hospitales, torres de consultorios o centros multiinstitución.

Su objetivo es ordenar el flujo desde que un paciente agenda o llega a una cita hasta que es llamado al consultorio, reduciendo filas, errores manuales y exposición innecesaria de datos personales. La solución combina una plataforma web administrativa, kioskos de autoservicio, pantallas públicas de turnos y una app móvil Android para recepción.

El sistema está diseñado para operar por institución, campus, torre, piso, sala, consultorio, médico y usuario, con permisos configurables y trazabilidad de eventos.

## Qué resuelve

- Registro ordenado de pacientes, citas y llegadas.
- Check-in por QR, por búsqueda manual o desde app móvil.
- Gestión de turnos visibles en pantallas públicas.
- Administración de múltiples instituciones, campus, torres, pisos y consultorios.
- Separación de permisos por rol, pantalla y ubicación física.
- Auditoría de cambios administrativos y eventos operativos.
- Reportes exportables para revisión operativa.
- Kioskos configurables por punto de acceso.
- Operación segura sin colocar datos clínicos o personales dentro del QR.

## Usuarios a los que está dirigido

- Administradores del sistema.
- Administradores de operación o negocio.
- Personal de recepción.
- Médicos.
- Operadores de atención o apoyo.
- Responsables de seguridad o control de accesos.
- Pacientes que realizan autoservicio en kiosko.
- Personal móvil que usa la app Android de llegada.

## Flujo funcional principal

```text
Paciente
  -> Registro o búsqueda
  -> Cita programada o espontánea
  -> Generación de QR y ticket lógico
  -> Llegada por kiosko, recepción o app móvil
  -> Autorización y llamado del turno
  -> Pantalla pública muestra turno y destino
  -> Auditoría y reportes operativos
```

## Módulos y funciones

### 1. Administración general

#### Dashboard

- Presenta un resumen rápido de la operación y configuración.
- Muestra conteos de instituciones, campus, usuarios, roles, consultorios, médicos, operadores y eventos de auditoría.
- Sirve como punto inicial para acceder a módulos operativos clave.

#### Perfil de usuario

- Permite al usuario consultar y actualizar su información básica.
- Permite cambio de contraseña.
- Soporta obligación de cambio de contraseña cuando una cuenta fue creada con contraseña temporal.

#### Autenticación

- Acceso mediante correo y contraseña.
- Manejo de sesión con token.
- Redirección a la pantalla inicial configurada para el rol del usuario.

### 2. Estructura institucional y física

#### Instituciones

- Alta y edición de instituciones.
- Activación y desactivación de instituciones.
- Registro de datos básicos como nombre, razón social y estado.
- Base para operar escenarios multiinstitución.

#### Campus

- Alta y edición de campus por institución.
- Activación y desactivación.
- Registro de ubicación o dirección operativa.
- Organización de sedes dentro de una institución.

#### Torres

- Alta y edición de torres por campus.
- Registro de número de pisos.
- Activación y desactivación.
- Soporte para edificios con una o varias torres.

#### Pisos

- Alta y edición de pisos por campus y torre.
- Código de piso y nombre visible.
- Identificación de pisos que cuentan con pantallas.
- Activación y desactivación.

#### Salas de espera

- Alta y edición de salas de espera.
- Asociación a campus, torre y piso.
- Registro de capacidad estimada.
- Activación y desactivación.

#### Consultorios

- Alta y edición de consultorios por campus, torre y piso.
- Código, nombre visible e instrucciones de acceso.
- Notas operativas.
- Asociación a clústers de turnos.
- Activación y desactivación.

#### Clústers de turnos

- Agrupación de consultorios o zonas de espera dentro de un piso.
- Permiten controlar qué turnos aparecen en qué pantalla.
- Activación y desactivación.
- Útiles cuando una misma planta tiene varias salas o áreas de atención.

### 3. Seguridad, roles y permisos

#### Usuarios

- Alta y edición de cuentas para personal administrativo, médico y operativo.
- Registro de nombre, apellidos, correo, correo alterno, teléfono y estado.
- Contraseña temporal o nueva.
- Opción de forzar cambio de contraseña.

#### Roles

- Creación y edición de roles.
- Activación y desactivación.
- Definición de pantalla inicial por rol.
- Permisos por pantalla con tres niveles:
  - Sin acceso.
  - Consultar.
  - Editar.

#### Asignación de roles a usuarios

- Relación de usuarios con roles activos.
- Alcance por institución, campus, torre, piso o consultorio.
- Vigencia con fecha de inicio y fecha de fin.
- Desactivación de asignaciones sin borrar historial.

#### Asignación de usuarios a médicos

- Permite que un usuario opere o consulte información asociada a uno o más médicos.
- Control de vigencias.
- Prevención de asignaciones duplicadas o traslapadas.

#### Búsqueda de usuarios

- Consulta de usuarios por nombre, ubicación, rol y estado.
- Muestra alcance operativo: instituciones, campus, torres y pisos.
- Exportación de resultados a Excel, CSV o JSON.

### 4. Médicos, operadores y asignaciones operativas

#### Médicos

- Alta y edición de médicos.
- Asociación opcional a usuario del sistema.
- Nombre visible para operación y pantallas.
- Plantilla configurable para texto de turno.
- Activación y desactivación.

#### Plantilla de turnos

- Configura cómo se mostrará el llamado en pantalla.
- Opciones disponibles:
  - Paciente y consultorio.
  - Turno, paciente y consultorio.
  - Paciente, turno y consultorio.
  - Turno y consultorio.

#### Operadores

- Alta y edición de operadores.
- Asociación a usuarios del sistema.
- Activación y desactivación.

#### Asignación médico-consultorio

- Relaciona médicos con consultorios.
- Controla vigencia por fecha.
- Puede incluir hora inicio, hora fin y días de semana.
- Permite activar o desactivar asignaciones.

#### Asignación de operador

- Asigna operadores a campus, médicos o consultorios.
- Maneja fecha de inicio, fecha fin y prioridad.
- Permite activar o desactivar asignaciones.

### 5. Pacientes

#### Alta de pacientes

- Registro de paciente por médico.
- Datos operativos: nombre, nombre preferido, apellidos, celular y fecha de nacimiento.
- Folio operativo automático.
- No administra expediente clínico.

#### Búsqueda de pacientes

- Consulta por nombre, celular o folio.
- Filtro por médico.
- Ordenamiento por nombre y folio.

#### Edición de pacientes

- Actualización de datos operativos.
- Validación de datos mínimos para identificación.
- Soporte para nombre preferido.

#### Activación, desactivación y marcado para borrar

- Permite retirar pacientes de operación activa sin eliminación física inmediata.
- Mantiene trazabilidad y reduce riesgos de pérdida accidental de información.

### 6. Citas

#### Citas programadas

- Creación de citas con fecha, hora, médico, paciente, campus, torre, piso y consultorio.
- Duración estimada.
- Notas operativas.
- Folio corto de turno generado automáticamente.

#### Citas espontáneas

- Registro de visitas no programadas cuando la operación lo requiera.
- Uso del mismo flujo de folio, ubicación y atención.

#### Prevención de duplicados

- Al crear una cita, el sistema advierte si detecta posibles duplicados.
- Permite confirmar o cancelar la creación.

#### Consulta de citas

- Listado por médico, fecha y hora de inicio.
- Paginación.
- Estado de cita visible.

#### Estados de cita

- Agendada.
- QR generado.
- Llegó a lobby.
- Autorizado para pasar.
- En consulta.
- Finalizada.
- No se presentó.
- Cancelada.
- Expirada.

### 7. Operación diaria de citas

#### Citas de hoy

- Tablero diario para operar las citas del día.
- Filtros por fecha, rango horario, estado, institución, campus, torre, piso, consultorio, médico y paciente.
- Acciones rápidas por cita.

#### Generación de QR

- Genera QR firmado por el servidor.
- El QR no contiene datos personales del paciente, médico, consultorio ni especialidad.
- Puede descargarse como imagen.

#### Ticket lógico

- Genera un ticket con fecha, leyenda, turno, QR, consultorio, torre, piso y hora.
- Preparado para impresión o entrega operativa.

#### Check-in de cita

- Registra llegada a lobby desde el tablero.
- Actualiza el estado operativo de la cita.

#### Autorización para pasar

- Permite marcar una cita como autorizada para avanzar al siguiente punto de atención.

#### Llamado de turno

- Envía el turno a la pantalla correspondiente.
- Registra número de llamado.
- Al tercer llamado, puede marcar la cita como no presentada según la regla operativa actual.

#### Cancelación

- Permite cancelar una cita desde la operación diaria.

#### Exportación de citas

- Exporta resultados filtrados a Excel, CSV o JSON.
- Registra evento de auditoría por exportación.

### 8. Recepción

#### Vista de recepción

- Diseñada para registrar llegadas de manera rápida.
- Filtros por institución, campus, torre, piso, paciente, médico, consultorio y hora de inicio.
- Paginación y ordenamiento.

#### Check-in desde recepción

- Permite marcar llegada de una cita.
- Muestra si una cita ya está registrada.

#### Deshacer check-in

- Permite revertir un check-in cuando la regla de tiempo lo permite.
- Ayuda a corregir errores operativos sin intervención técnica.

### 9. Check-in por QR

#### Lector de QR en recepción

- Campo optimizado para escáner físico o pegado manual del token.
- Enfoque rápido del lector.
- Registro de llegada contra el servidor.

#### Resultado de validación

- Muestra resultado operativo, mensaje y folio de turno.
- Mantiene listado de lecturas recientes para referencia inmediata.

### 10. Kioskos de autoservicio

#### Puntos de acceso

- Alta y edición de puntos de acceso por campus, torre y piso.
- Puede configurarse para una torre/piso específico o para todos.
- Activación y desactivación.

#### Alta y configuración de kioskos

- Registro de dispositivo por código.
- Token de seguridad por kiosko.
- Nombre y descripción.
- Asociación a punto de acceso.
- Activación y desactivación.
- Generación de URL del kiosko.

#### Personalización visual de kioskos

- Configuración de colores de fondo, texto, color primario y color de acento.
- Vista previa visual.
- Intervalo de consulta configurable.

#### Flujo de kiosko para pacientes

- Pantalla de bienvenida.
- Búsqueda de cita por nombre y apellido.
- Validación adicional por celular o fecha de nacimiento cuando hay homónimos.
- Registro de llegada de la cita encontrada.
- Check-in por QR.
- Resultado claro de la operación para el paciente.

### 11. App móvil Android

#### Inicio de sesión móvil

- Acceso con usuario autorizado.
- Sesión local de 12 horas con cierre automático.
- Conexión contra la API real del sistema.

#### Registro por QR

- Escaneo de QR con la cámara del celular.
- Validación siempre contra el servidor.
- Registro de llegada desde el dispositivo móvil.

#### Búsqueda manual

- Búsqueda por nombre del paciente más celular o fecha de nacimiento.
- Selección de cita encontrada.
- Registro de llegada.

#### Ticket PDF

- Obtención de ticket asociado a la cita.
- Generación de PDF para impresión virtual.

#### Log local del dispositivo

- Guarda actividad mínima del dispositivo.
- No guarda datos personales del paciente.
- Registra token QR, folio, fecha/hora y usuario de recepción.

### 12. Mobile PWA

#### Acceso móvil vía navegador

- Alternativa ligera para flujo móvil sin instalar APK.
- Consulta contra la API.

#### Búsqueda y registro de cita

- Búsqueda de paciente/cita.
- Registro de llegada.

#### QR manual

- Validación de token QR desde la PWA.

### 13. Pantallas públicas de turnos

#### Configuración de pantallas

- Alta y edición de pantallas por código de dispositivo.
- Token de dispositivo.
- Nombre visible.
- Alcance por campus, piso, clúster o consultorio.
- Activación y desactivación.

#### Configuración visual

- Intervalo de actualización.
- Tiempo de resaltado para turno nuevo.
- Tiempo visible.
- Número máximo de turnos en pantalla.
- Colores de fondo, texto, turno nuevo y turno normal.
- Tamaños de letra configurables.

#### Vista pública de turnos

- Muestra turno y consultorio o texto personalizado.
- Evita exponer información clínica o datos sensibles innecesarios.
- Indica conexión y última actualización.
- Incluye QR de identificación de la pantalla.

#### Voz en pantalla

- Puede anunciar turnos en voz alta desde navegadores compatibles.
- Preferencia local para activar o silenciar voz.

### 14. Turnos llamados

#### Consulta de turnos recientes

- Lista turnos llamados en un periodo configurable.
- Filtros por institución, campus, torre, piso, consultorio, médico y clúster.
- Accesos rápidos a "mi consultorio", "mi piso" y "mi clúster".

#### Re-llamado de turno

- Permite llamar nuevamente un turno.
- Controla el número de llamados.
- Evita re-llamar citas en estados no operables.

### 15. Contactos institucionales

#### Registro de contactos

- Alta y edición de responsables por institución.
- Tipos de contacto: primario, secundario, solo emergencias u otro.
- Medios de contacto: celular y correo.
- Notas internas.

#### Alcance de contactos

- Contacto aplicable a toda una institución.
- Asignación por campus.
- Asignación por torre.

#### Búsqueda de contactos

- Filtro por institución, campus, torre, nombre o correo.
- Paginación.
- Detalle de contacto y medios disponibles.

### 16. Reportes

#### Inventario jerárquico

- Reportes por:
  - Instituciones.
  - Campus.
  - Pisos.
  - Consultorios.
  - Salas de espera.
  - Clústers y pantallas.

#### Filtros de reporte

- Institución.
- Campus.
- Piso.
- Estado: todos, activos o inactivos.

#### Exportación

- Descarga de reportes en Excel, CSV o JSON.

### 17. Auditoría

#### Registro de eventos

- Consulta de eventos administrativos y operativos recientes.
- Fecha y hora.
- Tipo de evento.
- Entidad afectada.
- Usuario responsable o sistema.
- Valor posterior al cambio.

#### Trazabilidad

- Facilita investigación de cambios.
- Apoya controles internos.
- Reduce dependencia de bitácoras manuales.

## Seguridad y privacidad funcional

- El QR se firma en el servidor.
- El QR no contiene datos personales ni información clínica.
- El sistema guarda hash del token en lugar de depender de datos abiertos en el código.
- Los permisos limitan pantallas y alcance operativo.
- La auditoría registra acciones relevantes.
- Los catálogos se activan/desactivan en lugar de depender de borrados físicos.
- La app móvil valida contra servidor y no guarda datos personales del paciente en su log local.

## Plataformas incluidas

### Web administrativa y operativa

Portal principal para configuración, catálogos, seguridad, citas, recepción, reportes y auditoría.

### Kiosko web

Interfaz de autoservicio para pacientes en puntos de acceso.

### Pantalla pública de turnos

Vista diseñada para televisores o monitores de sala.

### Mobile PWA

Versión móvil web para flujos ligeros desde navegador.

### App Android

Aplicación móvil para recepción o personal operativo que requiere registrar llegadas desde celular.

### API central

Servicio que concentra reglas de negocio, validación, permisos, QR, citas, check-in, auditoría y persistencia.

## Beneficios para la operación

- Menos filas y menos captura repetida en recepción.
- Mayor control de quién puede ver o editar información.
- Reducción de errores al identificar pacientes con homónimos.
- Flujo consistente para recepción, kiosko y app móvil.
- Turnos visibles sin exponer datos innecesarios.
- Mejor trazabilidad de cambios y acciones.
- Reportes exportables para supervisión.
- Configuración adaptable a edificios pequeños, clínicas multi-sede o torres médicas complejas.

## Alcance actual y consideraciones

El sistema cubre administración operativa, control de llegada, QR, turnos, kioskos, app móvil, reportes y auditoría. No sustituye un expediente clínico, sistema de facturación, pagos, mensajería masiva o plataforma de historia médica.

La arquitectura está preparada para crecer hacia impresión física, notificaciones, integraciones externas, respaldos avanzados y otros módulos, manteniendo separadas las responsabilidades de operación, administración, kiosko, móvil y pantallas.
