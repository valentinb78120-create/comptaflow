"""Pydantic schemas for Invoice API I/O."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.invoice import InvoiceStatus


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str | None
    quantity: Decimal | None
    unit_price_ht: Decimal | None
    total_ht: Decimal | None
    tva_rate: Decimal | None
    pcg_account: str | None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cabinet_id: uuid.UUID
    original_filename: str
    status: InvoiceStatus

    vendor_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None

    amount_ht: Decimal | None
    amount_tva: Decimal | None
    amount_ttc: Decimal | None
    tva_rate: Decimal | None

    pcg_account: str | None
    pcg_label: str | None
    pcg_source: str | None

    ocr_confidence: float | None
    ocr_error: str | None

    line_items: list[LineItemOut] = []

    created_at: datetime
    updated_at: datetime


class InvoicePatch(BaseModel):
    """Fields the user can manually correct after OCR."""

    vendor_name: str | None = Field(None, max_length=512)
    invoice_number: str | None = Field(None, max_length=128)
    invoice_date: date | None = None
    due_date: date | None = None

    amount_ht: Decimal | None = Field(None, ge=0)
    amount_tva: Decimal | None = Field(None, ge=0)
    amount_ttc: Decimal | None = Field(None, ge=0)
    tva_rate: Decimal | None = Field(None, ge=0, le=100)

    pcg_account: str | None = Field(None, max_length=16)
    pcg_label: str | None = Field(None, max_length=255)


class InvoiceUploadResponse(BaseModel):
    id: uuid.UUID
    status: InvoiceStatus
    message: str
