"""
Mistral OCR integration.

Sends an uploaded file to Mistral's OCR endpoint and parses the structured
response into an InvoiceOCRResult.  Falls back to a stub when the API key is
absent (useful for local dev without burning API credits).
"""
from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"


class MistralNotConfiguredError(RuntimeError):
    """Raised when MISTRAL_API_KEY is missing — caller should fall back to Tesseract."""


# Schéma JSON demandé à Mistral pour l'annotation structurée du document.
INVOICE_ANNOTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": ["string", "null"], "description": "Nom du fournisseur émetteur de la facture"},
        "invoice_number": {"type": ["string", "null"], "description": "Numéro de la facture"},
        "invoice_date": {"type": ["string", "null"], "description": "Date de facture au format YYYY-MM-DD"},
        "due_date": {"type": ["string", "null"], "description": "Date d'échéance au format YYYY-MM-DD"},
        "amount_ht": {"type": ["number", "null"], "description": "Montant hors taxes en euros"},
        "amount_tva": {"type": ["number", "null"], "description": "Montant de la TVA en euros"},
        "amount_ttc": {"type": ["number", "null"], "description": "Montant toutes taxes comprises en euros"},
        "tva_rate": {"type": ["number", "null"], "description": "Taux de TVA en pourcentage (ex: 20)"},
    },
    "required": [],
    "additionalProperties": False,
}


@dataclass
class InvoiceOCRResult:
    """Parsed fields extracted from the OCR response."""
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    amount_ht: Decimal | None = None
    amount_tva: Decimal | None = None
    amount_ttc: Decimal | None = None
    tva_rate: Decimal | None = None
    confidence: float = 0.0
    raw_text: str = ""
    raw_response: dict = field(default_factory=dict)


async def run_ocr(file_path: Path, mime_type: str) -> InvoiceOCRResult:
    """
    Send *file_path* to Mistral OCR and return a parsed InvoiceOCRResult.

    Raises httpx.HTTPStatusError on non-2xx API responses.
    """
    if not settings.mistral_api_key:
        raise MistralNotConfiguredError("MISTRAL_API_KEY not set")

    file_bytes = file_path.read_bytes()
    b64_content = base64.b64encode(file_bytes).decode()

    payload = {
        "model": settings.mistral_ocr_model,
        "document": {
            "type": "document_url",
            "document_url": f"data:{mime_type};base64,{b64_content}",
        },
        "include_image_base64": False,
        # Extraction structurée : Mistral renvoie directement les champs
        # de la facture en JSON (document_annotation), plus fiable que
        # nos regex qui restent en fallback.
        "document_annotation_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "invoice_fields",
                "schema": INVOICE_ANNOTATION_SCHEMA,
            },
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            MISTRAL_OCR_URL,
            headers={
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

    raw = response.json()
    return _parse_mistral_response(raw)


def parse_invoice_text(text: str) -> InvoiceOCRResult:
    """
    Run all field extractors over raw OCR *text* and return a populated
    InvoiceOCRResult.  Shared by the Mistral and Tesseract pipelines.
    """
    result = InvoiceOCRResult(raw_text=text)

    result.vendor_name = _extract_vendor(text)
    result.invoice_number = _extract_invoice_number(text)
    result.invoice_date = _extract_date(text, label_pattern=r"(?:date\s+(?:de\s+)?facture|invoice\s+date)\s*[:\-]?\s*")
    result.due_date = _extract_date(text, label_pattern=r"(?:date\s+(?:d['''])?échéance|due\s+date|à\s+payer\s+avant)\s*[:\-]?\s*")
    result.amount_ht, result.amount_tva, result.amount_ttc = _extract_amounts(text)
    result.tva_rate = _extract_tva_rate(text)

    # Simple confidence heuristic: ratio of non-null core fields
    core_fields = [result.vendor_name, result.invoice_date, result.amount_ttc]
    result.confidence = sum(1 for f in core_fields if f is not None) / len(core_fields)

    return result


def _parse_mistral_response(raw: dict) -> InvoiceOCRResult:
    """
    Extract invoice fields from the Mistral OCR JSON response.

    Priorité à l'annotation structurée (document_annotation) si présente ;
    sinon fallback sur les regex appliquées au markdown des pages.
    """
    pages = raw.get("pages", [])
    full_text = "\n".join(p.get("markdown", "") for p in pages)

    annotated = _parse_document_annotation(raw)
    if annotated is not None:
        annotated.raw_text = full_text
        annotated.raw_response = raw
        return annotated

    result = parse_invoice_text(full_text)
    result.raw_response = raw
    return result


def _parse_document_annotation(raw: dict) -> InvoiceOCRResult | None:
    """
    Parse the structured `document_annotation` field returned by Mistral.
    Returns None when absent or unusable (the caller falls back to regex).
    """
    import json

    annotation = raw.get("document_annotation")
    if not annotation:
        return None

    try:
        data = json.loads(annotation) if isinstance(annotation, str) else dict(annotation)
    except (ValueError, TypeError):
        logger.warning("document_annotation illisible — fallback regex")
        return None

    def to_decimal(v) -> Decimal | None:
        if v is None:
            return None
        try:
            return Decimal(str(v))
        except InvalidOperation:
            return None

    def to_date(v) -> date | None:
        if not v:
            return None
        try:
            return date.fromisoformat(str(v)[:10])
        except ValueError:
            return None

    result = InvoiceOCRResult(
        vendor_name=data.get("vendor_name") or None,
        invoice_number=data.get("invoice_number") or None,
        invoice_date=to_date(data.get("invoice_date")),
        due_date=to_date(data.get("due_date")),
        amount_ht=to_decimal(data.get("amount_ht")),
        amount_tva=to_decimal(data.get("amount_tva")),
        amount_ttc=to_decimal(data.get("amount_ttc")),
        tva_rate=to_decimal(data.get("tva_rate")),
    )

    core_fields = [result.vendor_name, result.invoice_date, result.amount_ttc]
    result.confidence = sum(1 for f in core_fields if f is not None) / len(core_fields)
    # L'extraction structurée est plus fiable que les regex : bonus de confiance
    if result.confidence == 1.0:
        result.confidence = 0.95  # jamais 100% — l'humain reste responsable

    return result


# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------

def _extract_vendor(text: str) -> str | None:
    """Try to find vendor name from common invoice header patterns."""
    patterns = [
        r"(?:émis\s+par|fournisseur|vendor|from)\s*[:\-]?\s*([A-ZÀ-Ÿa-zà-ÿ0-9 &.,'-]{2,80})",
        r"^([A-ZÀÂÆÇÉÈÊËÎÏÔŒÙÛÜ][A-ZÀ-Ÿa-zà-ÿ0-9 &.,'-]{2,60})(?:\n|$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def _extract_invoice_number(text: str) -> str | None:
    """Extract invoice / reference number."""
    m = re.search(
        r"(?:facture\s+n[°o]?|invoice\s+(?:no|#|number)|n[°o]\s+facture|référence|ref\.?)\s*[:\-]?\s*([A-Z0-9/_\-]{3,32})",
        text,
        re.IGNORECASE,
    )
    return m.group(1).strip() if m else None


def _extract_date(text: str, label_pattern: str) -> date | None:
    """
    Extract a date that follows *label_pattern*.
    Supports DD/MM/YYYY, DD-MM-YYYY and DD.MM.YYYY.

    Named groups keep the indices stable regardless of how many groups
    *label_pattern* itself contains.
    """
    date_re = r"(?P<day>\d{1,2})[/\-.](?P<month>\d{1,2})[/\-.](?P<year>\d{4})"

    for pattern in (label_pattern + date_re, date_re):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return date(int(m.group("year")), int(m.group("month")), int(m.group("day")))
            except ValueError:
                continue  # ex: 45/13/2026 — on tente le fallback
    return None


def _parse_amount(raw: str) -> Decimal | None:
    """Convert a string like '1 234,56' or '1234.56' to Decimal."""
    cleaned = raw.replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _extract_amounts(text: str) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Return (amount_ht, amount_tva, amount_ttc)."""
    ht_pattern = r"(?:montant\s+HT|total\s+HT|sous[\s\-]total\s+HT|base\s+HT)\s*[:\-]?\s*([\d\s,.']+)\s*(?:€|EUR)?"
    # Le taux ("20 %") peut apparaître avant ou après le séparateur ":"
    tva_pattern = r"(?:TVA|taxe\s+sur\s+(?:la\s+)?valeur\s+ajoutée|VAT)(?:\s+à)?\s*(?:\d+(?:[.,]\d+)?\s*%)?\s*[:\-]?\s*([\d\s,.']+)\s*(?:€|EUR)?"
    ttc_pattern = r"(?:montant\s+TTC|total\s+TTC|total\s+à\s+payer|net\s+à\s+payer|total\s+(?:général\s+)?TTC)\s*[:\-]?\s*([\d\s,.']+)\s*(?:€|EUR)?"

    def first_match(pattern: str) -> Decimal | None:
        m = re.search(pattern, text, re.IGNORECASE)
        return _parse_amount(m.group(1)) if m else None

    return first_match(ht_pattern), first_match(tva_pattern), first_match(ttc_pattern)


def _extract_tva_rate(text: str) -> Decimal | None:
    """Extract the TVA rate (e.g. 20%, 10%, 5.5%)."""
    m = re.search(r"TVA\s+(?:à\s+)?(\d+(?:[.,]\d+)?)\s*%", text, re.IGNORECASE)
    if m:
        return _parse_amount(m.group(1))
    return None
