from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Usuario(TimestampMixin, Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(64))
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    estado: Mapped[str] = mapped_column(String(32), default="ACTIVO", server_default="ACTIVO", nullable=False)
