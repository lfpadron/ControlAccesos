from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ContactoInstitucional(TimestampMixin, Base):
    __tablename__ = "contactos_institucionales"
    __table_args__ = (
        CheckConstraint(
            "tipo_contacto IN ('PRIMARIO', 'SECUNDARIO', 'SOLO_EMERGENCIAS', 'OTRO')",
            name="ck_contactos_institucionales_tipo_contacto_valido",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    medios_contacto: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    tipo_contacto: Mapped[str] = mapped_column(String(32), nullable=False)
    tipo_contacto_descripcion: Mapped[str | None] = mapped_column(String(50))
    notas: Mapped[str | None] = mapped_column(Text)


class ContactoInstitucionalComplejo(Base):
    __tablename__ = "contactos_institucionales_complejos"

    contacto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contactos_institucionales.id", name="fk_contacto_complejo_contacto", ondelete="CASCADE"),
        primary_key=True,
    )
    complejo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("complejos.id", name="fk_contacto_complejo_complejo"),
        primary_key=True,
    )
