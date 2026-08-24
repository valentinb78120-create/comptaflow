"""Règle de catégorisation PCG personnalisée, propre à un cabinet."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PCGCustomRule(Base):
    __tablename__ = "pcg_custom_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cabinet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cabinets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Liste de mots-clés déclencheurs (match insensible à la casse, mots entiers)
    keywords: Mapped[list] = mapped_column(JSON, nullable=False)
    account: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PCGCustomRule cabinet={self.cabinet_id} {self.keywords}→{self.account}>"
