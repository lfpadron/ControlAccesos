# App de Médicos

App Flutter Android separada de la app de acceso por QR. Está dirigida a médicos y asistentes para consultar agenda, gestionar citas, generar QR de acceso, llamar pacientes y ver cuándo recepción registró el check-in.

## Funciones

- Login con usuario y contraseña contra `/auth/login`.
- Validación de permisos desde `/auth/me`; requiere acceso a `pacientes` y `citas`.
- Consulta de agenda por fecha, médico, paciente, estado y tipo de cita.
- Consulta de pacientes accesibles por médico.
- Creación de citas `PROGRAMADA` y `ESPONTANEA`.
- Cancelación de citas mediante la ruta existente `/citas/{id}/cancelar`.
- Generación y visualización de QR de acceso mediante `/citas/{id}/qr`.
- Llamado a pacientes mediante `/citas/{id}/llamar`.
- Refresco periódico de la agenda para mostrar estados como `LLEGO_LOBBY`.

## Servidor

La URL por defecto apunta a:

```bash
https://control-acceso-qr.com.mx/api
```

Puede sobrescribirse al ejecutar:

```bash
flutter run --dart-define=DOCTORS_API_BASE_URL=http://192.168.1.50:8080/api
```

## Build Android

```bash
flutter pub get
flutter build apk --debug
```

APK generado:

```text
build/app/outputs/flutter-apk/app-debug.apk
```

## iOS Futuro

El código de la app es Flutter. Cuando se requiera iOS, se puede agregar la plataforma iOS al mismo proyecto y reutilizar pantallas, modelos y cliente API.
