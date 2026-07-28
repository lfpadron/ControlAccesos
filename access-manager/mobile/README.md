# App Android de llegada de pacientes

App Flutter Android para registrar llegada de pacientes desde un celular, sin instalar un kiosko físico.

## Funciones

- Login de usuario con rol `RECEPCIONISTA`, `ADMIN_NEGOCIO` o `ADMIN_SISTEMA`.
- Sesión local de 12 horas con cierre automático.
- Escaneo de QR con la cámara del celular.
- Búsqueda manual por nombre más celular o fecha de nacimiento.
- Validación y check-in siempre contra el servidor.
- Ticket PDF mediante impresora virtual.
- Log local SQLite sin datos personales del paciente: token QR, folio de cita, fecha/hora y login de recepción.

## Servidor

La URL por defecto para emulador Android es:

```bash
http://10.0.2.2:8080/api
```

Para un celular físico use la IP LAN del servidor:

```bash
flutter run --dart-define=ACCESS_API_BASE_URL=http://192.168.1.50:8080/api
```

También puede cambiarse desde la pantalla de login.

## Build

```bash
flutter pub get
flutter build apk --debug
```

APK generado:

```text
build/app/outputs/flutter-apk/app-debug.apk
```
