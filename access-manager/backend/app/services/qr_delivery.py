"""QR images and immediate delivery. No delivery history or automatic retries."""
from __future__ import annotations

import base64
from io import BytesIO
import re

import httpx
from PIL import Image, ImageDraw, ImageFont
import qrcode
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.flow import Cita, Paciente
from app.models.operational import Consultorio, Piso, Torre
from app.schemas.qr_delivery import QrDestination


class DeliveryError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def normalize_mobile(value: str | None) -> str | None:
    """Ten digits mean Mexico; international numbers include their country code."""
    if not value or not re.fullmatch(r"\+?[0-9 ().-]+", value.strip()):
        return None
    digits = re.sub(r"[^0-9]", "", value)
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        digits = "52" + digits
    if len(digits) == 13 and digits.startswith("521"):
        digits = "52" + digits[3:]
    return digits if 11 <= len(digits) <= 15 and not digits.startswith("0") else None


def mobile_contacts(patient: Paciente):
    for position, phone, kind in (
        (1, patient.telefono_1, patient.tipo_telefono_1),
        (2, patient.celular, patient.tipo_telefono_2),
    ):
        if phone and kind == "CELULAR":
            yield position, phone, getattr(patient, f"telegram_chat_id_{position}")


def phone_label(position: int, phone: str) -> str:
    return f"Celular {position} ····{re.sub(r'[^0-9]', '', phone)[-4:]}"


def telegram_bot_url() -> str | None:
    settings = get_settings()
    username = (settings.telegram_bot_username or "").strip().lstrip("@")
    if not (settings.telegram_bot_token and settings.telegram_webhook_secret and re.fullmatch(r"[A-Za-z0-9_]{5,32}", username)):
        return None
    return f"https://t.me/{username}?start=cmc"


def destinations(patient: Paciente) -> list[QrDestination]:
    settings = get_settings()
    options: list[QrDestination] = []
    if patient.correo_electronico:
        ready = bool(settings.resend_api_key and settings.qr_email_from)
        options.append(QrDestination(
            metodo="CORREO", etiqueta=f"Correo — {patient.correo_electronico}",
            disponible=ready, motivo=None if ready else "El envío por correo aún no está configurado.",
        ))
    configured = telegram_bot_url() is not None
    for position, phone, chat_id in mobile_contacts(patient):
        valid = normalize_mobile(phone) is not None
        reason = None
        if not configured:
            reason = "El envío por Telegram aún no está configurado."
        elif not valid:
            reason = "Revisa el celular: usa 10 dígitos de México o un número internacional con código de país."
        elif not chat_id:
            reason = "El paciente debe vincular este celular con Telegram."
        options.append(QrDestination(
            metodo=f"TELEGRAM_{position}", etiqueta=f"Telegram — {phone_label(position, phone)}",
            disponible=reason is None, motivo=reason, vinculable=configured and valid,
        ))
    return options


def qr_details(db: Session, cita: Cita) -> list[str]:
    def prefixed(label: str, value: str) -> str:
        text = value.strip()
        return text if text.casefold().startswith(label.casefold()) else f"{label} {text}"

    consultorio = db.get(Consultorio, cita.consultorio_id)
    piso = db.get(Piso, cita.piso_id)
    torre = db.get(Torre, piso.torre_id) if piso else None
    lines = [f"Cita {cita.fecha_cita:%d/%m/%Y} {cita.hora_cita:%H:%M} hrs", f"Turno {cita.folio_turno}"]
    if torre:
        lines.append(prefixed("Torre", torre.nombre))
    if piso:
        lines.append(prefixed("Piso", piso.nombre_visible or str(piso.numero)))
    if consultorio:
        name = (consultorio.nombre_visible or "").strip()
        lines.append(f"{name} - {consultorio.codigo}" if name else prefixed("Consultorio", consultorio.codigo))
    return lines


def _font(size: int):
    for name in ("DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def render_qr_png(token: str, details: list[str]) -> bytes:
    # Keep integer-sized QR modules and a four-module quiet zone for scanning.
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=4)
    qr.add_data(token)
    qr.make(fit=True)
    matrix = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    width = max(640, matrix.width + 64)
    font = _font(24)
    measurement = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines: list[str] = []
    for detail in details:
        line = ""
        for character in detail:
            if line and measurement.textlength(line + character, font=font) > width - 80:
                lines.append(line)
                line = ""
            line += character
        lines.append(line)
    image = Image.new("RGB", (width, matrix.height + len(lines) * 36 + 72), "white")
    image.paste(matrix, ((width - matrix.width) // 2, 24))
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        left = (width - draw.textlength(line, font=font)) / 2
        draw.text((left, matrix.height + 40 + index * 36), line, font=font, fill="black")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def qr_filename(cita: Cita) -> str:
    return f"{cita.folio_turno}_{cita.fecha_cita}_{cita.hora_cita:%H-%M}.png"


def provider_post(provider: str, url: str, **kwargs) -> dict:
    try:
        with httpx.Client(timeout=get_settings().qr_delivery_timeout_seconds) as client:
            response = client.post(url, **kwargs)
        if response.status_code == 429:
            raise DeliveryError(f"{provider} alcanzó su límite de envíos. Intenta más tarde.", 429)
        if not response.is_success:
            raise DeliveryError(f"{provider} rechazó el envío. Revisa la configuración y el destinatario.")
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid response")
        return data
    except (httpx.HTTPError, ValueError):
        # Never surface provider URLs, credentials, raw responses or exceptions.
        raise DeliveryError(
            f"No fue posible confirmar el envío con {provider}. Comprueba si llegó antes de reintentar."
        ) from None


def send_email(address: str, png: bytes, filename: str, details: list[str]) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.qr_email_from:
        raise DeliveryError("El envío por correo aún no está configurado.", 503)
    payload = {
        "from": settings.qr_email_from, "to": [address],
        "subject": "CMC — QR para tu cita",
        "text": "Presenta el QR adjunto al llegar.\n\n" + "\n".join(details),
        "attachments": [{"filename": filename, "content": base64.b64encode(png).decode("ascii")}],
    }
    if settings.qr_email_reply_to:
        payload["reply_to"] = settings.qr_email_reply_to
    data = provider_post("Resend", "https://api.resend.com/emails",
                         headers={"Authorization": f"Bearer {settings.resend_api_key}"}, json=payload)
    if not data.get("id"):
        raise DeliveryError("Resend no confirmó el envío. Comprueba si llegó antes de reintentar.")


def telegram_request(method: str, **kwargs) -> dict:
    token = get_settings().telegram_bot_token
    if not token:
        raise DeliveryError("El envío por Telegram aún no está configurado.", 503)
    data = provider_post("Telegram", f"https://api.telegram.org/bot{token}/{method}", **kwargs)
    if data.get("ok") is not True:
        raise DeliveryError("Telegram rechazó el envío. El paciente debe abrir el bot y revisar la vinculación.")
    return data


def send_telegram(chat_id: int, png: bytes, filename: str, details: list[str]) -> None:
    # Send as a document so Telegram keeps the QR pixels intact.
    telegram_request("sendDocument", data={"chat_id": str(chat_id), "caption": "Presenta este QR al llegar.\n" + "\n".join(details)[:900]},
                     files={"document": (filename, png, "image/png")})


def link_verified_phone(db: Session, phone: str, chat_id: int) -> int:
    normalized = normalize_mobile(phone)
    if not normalized:
        return 0
    variants = {normalized, "00" + normalized}
    if normalized.startswith("52") and len(normalized) == 12:
        variants.update({normalized[2:], "521" + normalized[2:], "00521" + normalized[2:]})
    # The same registered contact may receive QR codes for several family members.
    patients = db.scalars(select(Paciente).where(
        Paciente.activo.is_(True), Paciente.marcado_borrado_en.is_(None),
        or_(
            and_(Paciente.tipo_telefono_1 == "CELULAR", func.regexp_replace(Paciente.telefono_1, "[^0-9]", "", "g").in_(variants)),
            and_(Paciente.tipo_telefono_2 == "CELULAR", func.regexp_replace(Paciente.celular, "[^0-9]", "", "g").in_(variants)),
        ),
    ).with_for_update()).all()
    count = 0
    for patient in patients:
        for position, stored_phone, _ in mobile_contacts(patient):
            if normalize_mobile(stored_phone) == normalized:
                setattr(patient, f"telegram_chat_id_{position}", chat_id)
                count += 1
    db.flush()
    return count


def unlink_chat(db: Session, chat_id: int) -> None:
    for column in (Paciente.telegram_chat_id_1, Paciente.telegram_chat_id_2):
        db.execute(update(Paciente).where(column == chat_id).values({column: None}))


def handle_telegram_update(db: Session, update_payload: dict) -> None:
    message = update_payload.get("message")
    if not isinstance(message, dict):
        return
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    if chat.get("type") != "private" or not isinstance(chat_id, int) or chat_id <= 0 or sender.get("id") != chat_id or sender.get("is_bot"):
        return
    text = str(message.get("text") or "")
    contact = message.get("contact")
    markup = {"remove_keyboard": True}
    if text.split(" ")[0] == "/stop":
        unlink_chat(db, chat_id)
        reply = "Desvinculamos este chat de CMC. Ya no recibirás QR aquí."
    elif isinstance(contact, dict):
        if contact.get("user_id") != sender.get("id"):
            reply = "Usa el botón Compartir mi celular. No se puede vincular el contacto de otra persona."
        else:
            linked = link_verified_phone(db, str(contact.get("phone_number") or ""), chat_id)
            reply = ("Celular vinculado. El personal de CMC ya puede enviarte el QR."
                     if linked else "Este celular no coincide con un celular registrado en CMC. Solicita al personal revisar tus datos y vuelve a compartirlo.")
    elif text.split(" ")[0] == "/start":
        reply = "Para recibir tu QR de CMC, comparte tu propio celular con el botón. Debe coincidir con el registrado en CMC. Puedes desvincularlo con /stop."
        markup = {"keyboard": [[{"text": "Compartir mi celular", "request_contact": True}]],
                  "resize_keyboard": True, "one_time_keyboard": True}
    else:
        return
    db.commit()
    telegram_request("sendMessage", json={"chat_id": chat_id, "text": reply, "reply_markup": markup})
