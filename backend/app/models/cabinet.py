"""Cabinet model — represents an accounting firm (B2B customer)."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Cabinet(Base):
    __tablename__ = "cabinets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    siret: Mapped[str | None] = mapped_column(String(14), nullable=True)
    # Null pour les cabinets démo (créés sans compte) — login impossible
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Accès au back-office /admin (stats, gestion des cabinets)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Clés des règles PCG standard désactivées par CE cabinet (ex: ["606100:Énergie électrique"])
    disabled_pcg_rules: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Plan tarifaire : decouverte / cabinet / cabinet_plus / illimite (voir core/plans.py)
    plan: Mapped[str] = mapped_column(String(32), default="cabinet", nullable=False)

    # Stripe
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    invoices: Mapped[list["Invoice"]] = relationship(  # noqa: F821
        "Invoice", back_populates="cabinet", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Cabinet id={self.id} name={self.name!r}>"
