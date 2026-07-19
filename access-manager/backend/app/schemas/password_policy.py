from __future__ import annotations

PASSWORD_REQUIREMENTS_MESSAGE = "La contraseña debe tener al menos 8 caracteres y al menos 1 número."


def validate_user_password(value: str | None) -> str | None:
    if value is None:
        return value
    if not any(char.isdigit() for char in value):
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
    return value
