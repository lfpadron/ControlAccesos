from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings
from app.models.flow import Cita


def appointment_datetime_utc(cita: Cita, zona_horaria: str = "UTC") -> datetime:
    try:
        timezone = ZoneInfo(zona_horaria)
    except ZoneInfoNotFoundError:
        timezone = UTC
    return datetime.combine(cita.fecha_cita, cita.hora_cita, tzinfo=timezone).astimezone(UTC)


def checkin_window_status(cita: Cita, timestamp: datetime | None = None, zona_horaria: str = "UTC") -> tuple[str, str]:
    settings = get_settings()
    current = timestamp or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    appointment_at = appointment_datetime_utc(cita, zona_horaria)
    minutes = (appointment_at - current).total_seconds() / 60

    if -settings.checkin_green_after_minutes <= minutes <= settings.checkin_green_before_minutes:
        return "VERDE", "Llegada registrada dentro de la ventana permitida."
    if settings.checkin_green_before_minutes < minutes <= settings.checkin_yellow_before_minutes:
        return "AMARILLO", "La cita es válida, pero el paciente llegó con mucha anticipación."
    return "ROJO", "La cita está fuera de la ventana inicial permitida."
