# Envío de QR por correo y Telegram

En **Citas** y **Citas de hoy**, pulsa **QR** para abrir el panel inferior.
**Enviar QR** muestra Bajar, el correo y una opción Telegram por cada celular,
identificada por posición y últimos cuatro dígitos. Selecciona el destino y pulsa
**Confirmar**; **Cancelar** cierra la selección sin enviar. El permiso de edición
de Citas o Citas de hoy habilita los envíos. Consultar permite ver y descargar.

El correo usa Resend por HTTPS; Telegram envía el PNG como documento, conservando
la resolución. La descarga, la vista y los envíos utilizan el mismo contenido QR.
Mostrar o reenviar recupera el QR vigente. Las citas canceladas, expiradas o no
presentadas no permiten compartirlo. Si cambian la cita, el contacto o la vigencia
después de mostrarlo, el servidor solicita **Actualizar QR y destinos**.

No se almacenan historial, contadores, banderas de envío ni archivos PNG. No hay
colas ni reintentos automáticos. Si ocurre un timeout, el resultado podría ser
incierto: comprobar la recepción antes de reintentar. El resultado de Resend
indica aceptación del mensaje, no confirmación de entrega o lectura.

## Configuración del servidor

Variables opcionales en `access-manager/.env` (Compose ya carga este archivo):

| Variable | Uso |
| --- | --- |
| `RESEND_API_KEY` | Clave de Resend con permiso de envío. |
| `QR_EMAIL_FROM` | Remitente autorizado, por ejemplo `CMC <citas@tu-dominio>`. |
| `QR_EMAIL_REPLY_TO` | Opcional: dirección atendida que recibe respuestas. |
| `TELEGRAM_BOT_TOKEN` | Credencial del bot entregada por BotFather. |
| `TELEGRAM_BOT_USERNAME` | Nombre del bot, sin `@`. |
| `TELEGRAM_WEBHOOK_SECRET` | Secreto aleatorio exclusivo del webhook; 1–256 caracteres A–Z, a–z, 0–9, `_` o `-`. |
| `QR_DELIVERY_TIMEOUT_SECONDS` | Timeout de las llamadas a proveedores; predeterminado 15 segundos. |

Las credenciales quedan en el servidor, nunca en el frontend ni en Git. Cuando
un canal carece de configuración, la pantalla explica que no está disponible.
El backend requiere salida HTTPS por el puerto 443. Telegram también necesita
acceder por HTTPS público a `/api/telegram/webhook`; Caddy ya enruta `/api/*`.

Después de configurar el entorno, desde `access-manager`:

```bash
docker compose build backend frontend
docker compose run --rm backend uv run alembic upgrade head
docker compose up -d backend frontend
```

La migración `202609270001` agrega únicamente `telegram_chat_id_1` y
`telegram_chat_id_2`, ambos opcionales, a pacientes. Respaldar la base antes de
aplicar migraciones, conforme al procedimiento habitual del despliegue.

## Resend

1. Crear una cuenta y una API key con permiso para enviar.
2. Para probar sin dominio propio, usar `QR_EMAIL_FROM=onboarding@resend.dev` y
   **como destinatario la misma dirección asociada a la cuenta de Resend**.
   Se puede registrar la cuenta con Yahoo y usar ese Yahoo para la cita de prueba.
3. Para enviar a pacientes, verificar un dominio institucional en Resend,
   agregar sus registros DNS y cambiar `QR_EMAIL_FROM` a ese dominio.
4. En un paciente de prueba, guardar el correo permitido. Abrir su cita,
   seleccionar **Correo — dirección**, confirmar y revisar el correo recibido.

El PNG va adjunto en la petición HTTPS; no se publica en un enlace ni requiere
configurar SMTP. Referencias: [API](https://resend.com/docs/api-reference/emails/send-email),
[adjuntos](https://resend.com/docs/dashboard/emails/attachments) y
[restricciones de prueba](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain).

## Telegram

1. Crear el bot en [BotFather](https://t.me/BotFather). Configurar su token,
   username y un secreto del webhook en el entorno del backend.
2. Con el backend publicado por HTTPS, registrar el webhook:

   ```bash
   docker compose exec backend python -m app.services.configure_telegram --url https://tu-dominio/api/telegram/webhook
   ```

   Este comando lee las credenciales del entorno y no las imprime. Se ejecuta
   al activar el bot o cambiar la URL/secreto, no en cada arranque. No se debe
   compartir el mismo bot entre entornos con webhooks diferentes.

3. Guardar el teléfono del paciente con tipo **CELULAR**. Diez dígitos se
   interpretan como un número mexicano; para otros países, usar el número
   internacional con código de país. Los números mexicanos antiguos `+521`
   también se reconocen.
4. En **Pacientes → Telegram → Vincular Telegram**, o desde el selector de envío
   de una cita, mostrar/copiar el enlace del bot. El paciente lo abre en su
   propia cuenta de Telegram, pulsa **Iniciar** y **Compartir mi celular**.
   El código que acompaña al enlace sólo abre el bot; no es un QR de acceso.
   **Copiar QR y enlace** permite pegarlo en otra aplicación para reenviarlo.
   El portapapeles incluye imagen, texto y, cuando está disponible, HTML con
   enlace pulsable. Cada aplicación decide qué formato pegar: el PNG también
   lleva el enlace escrito. **Copiar enlace** conserva la alternativa de texto.
   La copia requiere HTTPS (o localhost para desarrollo) y permiso del navegador;
   la pantalla avisa si no puede copiar. No se envía nada al copiar.
5. El webhook verifica su secreto, que sea un chat privado y que el contacto
   compartido pertenezca al propio remitente. Vincula sólo teléfonos celulares
   coincidentes en pacientes activos, sin revelar nombres ni datos de citas.
   Un teléfono familiar registrado en varios pacientes se vincula en todos
   ellos; los envíos siguen siendo individuales y sujetos a los permisos de CMC.
6. Pulsar **Actualizar** en Pacientes o **Actualizar QR y destinos** en la cita.
   Seleccionar Telegram del celular deseado y confirmar el envío.

Un paciente con dos celulares puede vincular cada uno desde la cuenta Telegram
correspondiente. Un teléfono fijo no aparece como destino. Cambiar el número
o su tipo elimina su vinculación; se debe volver a compartir el celular en el
bot después de guardar. Un paciente nuevo tampoco hereda vínculos de otros
registros: debe compartir de nuevo el contacto. **Desvincular** en Pacientes
quita sólo ese vínculo; `/stop` en el bot desvincula ese chat de todos los
pacientes asociados. Bloquear el bot también impedirá futuros envíos.

Referencias: [contactos y botones](https://core.telegram.org/bots/api#keyboardbutton),
[webhooks](https://core.telegram.org/bots/api#setwebhook) y
[documentos](https://core.telegram.org/bots/api#senddocument).

## Verificación

Las pruebas `backend/tests/test_qr_delivery.py` usan SQLite y proveedores
simulados; no envían mensajes ni necesitan credenciales. Cubren permisos,
cancelaciones, QR vigente, cambios de contacto, selección de ambos celulares,
vinculación, desvinculación y errores externos. Ejecutar desde `backend`:

```bash
uv run pytest tests/test_qr_delivery.py -q
```

Antes de activar con pacientes, realizar un envío con una cita de prueba a un
correo propio y a un celular vinculado, abrir el PNG y comprobar su lectura con
el lector de CMC. No basta con que el proveedor acepte la petición.
