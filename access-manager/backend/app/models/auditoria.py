from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evento: Mapped[str] = mapped_column(String(120), nullable=False)
    entidad: Mapped[str] = mapped_column(String(120), nullable=False)
    entidad_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    canal: Mapped[str | None] = mapped_column(String(64))
    ip_origen: Mapped[str | None] = mapped_column(String(64))
    valor_antes: Mapped[dict | None] = mapped_column(JSONB)
    valor_despues: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
