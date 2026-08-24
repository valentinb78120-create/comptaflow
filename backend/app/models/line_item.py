"""LineItem model — individual line on an invoice (optional granularity)."""
import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )

    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit_price_ht: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_ht: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tva_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Per-line PCG account (may differ from invoice-level)
    pcg_account: Mapped[str | None] = mapped_column(String(16), nullable=True)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="line_items")

    def __repr__(self) -> str:
        return f"<LineItem id={self.id} description={self.description!r} total_ht={self.total_ht}>"
