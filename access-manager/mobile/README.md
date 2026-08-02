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
- Icono y pantalla de acceso con imagen de Clínicas Alfa.

## Servidor real

La URL por defecto de la app apunta a la API real:

```bash
https://control-acceso-qr.com.mx/api
```

Para probar contra staging o un servidor local puede sobrescribirse al ejecutar:

```bash
flutter run --dart-define=ACCESS_API_BASE_URL=http://192.168.1.50:8080/api
```

También puede cambiarse desde la pantalla de login.

La app intenta usar las rutas móviles autenticadas (`/mobile/*`). Si la API real todavía no las tiene desplegadas, cae al flujo operativo existente (`/auth/me`, `/citas/buscar`, `/qr/checkin`, `/citas/{id}/checkin-lobby` y `/citas/{id}/ticket`) para poder mostrar el flujo completo contra datos reales.

## Build

```bash
flutter pub get
flutter build apk --debug
```

APK generado:

```text
build/app/outputs/flutter-apk/app-debug.apk
```
