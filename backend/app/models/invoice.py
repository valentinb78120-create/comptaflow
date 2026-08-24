"""Invoice model — one uploaded document going through the OCR pipeline."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, JSON, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InvoiceStatus(str, Enum):
    PENDING = "pending"        # file uploaded, waiting for OCR job
    PROCESSING = "processing"  # OCR job running
    NEEDS_REVIEW = "needs_review"  # OCR done but low-confidence fields
    VALIDATED = "validated"    # human confirmed / corrected
    EXPORTED = "exported"      # CSV has been generated


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cabinet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cabinets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # File storage
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    # SHA-256 du contenu — détection de doublons par cabinet
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Pipeline status
    status: Mapped[InvoiceStatus] = mapped_column(
        String(32), nullable=False, default=InvoiceStatus.PENDING, index=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ocr_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw OCR output stored for debugging / reprocessing
    ocr_raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Extracted fields (post-parsing)
    vendor_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    amount_ht: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_tva: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_ttc: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tva_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # PCG categorization
    pcg_account: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pcg_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pcg_source: Mapped[str | None] = mapped_column(
        String(32), nullable=True  # "auto" | "manual"
    )

    # OCR confidence score 0.0–1.0
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cabinet: Mapped["Cabinet"] = relationship(  # noqa: F821
        "Cabinet", back_populates="invoices"
    )
    line_items: Mapped[list["LineItem"]] = relationship(
        "LineItem", back_populates="invoice", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} vendor={self.vendor_name!r} status={self.status}>"
