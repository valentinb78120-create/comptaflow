"""Celery application instance and OCR task."""
import asyncio
import logging
from pathlib import Path

from celery import Celery
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "comptaflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_invoice_ocr(self, invoice_id: str) -> dict:
    """
    Celery task: run OCR on the invoice file and persist results.

    Uses a synchronous SQLAlchemy session because Celery workers are
    synchronous; async OCR calls are bridged via asyncio.run().
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.pcg_rule import PCGCustomRule
    from app.services.mistral_ocr import MistralNotConfiguredError, run_ocr
    from app.services.pcg_categorizer import PCGRule, categorize
    from app.services.tesseract_ocr import run_tesseract

    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        invoice: Invoice | None = db.get(Invoice, invoice_id)
        if invoice is None:
            logger.error("Invoice %s not found", invoice_id)
            return {"error": "not_found"}

        invoice.status = InvoiceStatus.PROCESSING
        db.commit()

        try:
            file_path = Path(invoice.storage_path)
            ocr_engine = "mistral"

            try:
                ocr_result = asyncio.run(run_ocr(file_path, invoice.file_mime_type))
            except MistralNotConfiguredError:
                logger.info("Mistral non configuré — fallback Tesseract pour %s", invoice_id)
                ocr_engine = "tesseract"
                ocr_result = run_tesseract(file_path, invoice.file_mime_type)
            except Exception as mistral_exc:
                # API down, 4xx/5xx, timeout… on tente Tesseract avant d'abandonner
                logger.warning("Mistral a échoué (%s) — fallback Tesseract pour %s", mistral_exc, invoice_id)
                ocr_engine = "tesseract"
                ocr_result = run_tesseract(file_path, invoice.file_mime_type)
                invoice.ocr_error = f"Mistral indisponible (fallback Tesseract): {mistral_exc}"

            invoice.ocr_raw_response = {**(ocr_result.raw_response or {}), "engine": ocr_engine}
            invoice.vendor_name = ocr_result.vendor_name
            invoice.invoice_number = ocr_result.invoice_number
            invoice.invoice_date = ocr_result.invoice_date
            invoice.due_date = ocr_result.due_date
            invoice.amount_ht = ocr_result.amount_ht
            invoice.amount_tva = ocr_result.amount_tva
            invoice.amount_ttc = ocr_result.amount_ttc
            invoice.tva_rate = ocr_result.tva_rate
            invoice.ocr_confidence = ocr_result.confidence

            # Auto-categorize — règles custom prioritaires, règles standard
            # désactivées par le cabinet ignorées
            custom_rows = db.execute(
                select(PCGCustomRule).where(PCGCustomRule.cabinet_id == invoice.cabinet_id)
            ).scalars().all()
            custom_rules = [PCGRule(r.keywords, r.account, r.label) for r in custom_rows]

            from app.models.cabinet import Cabinet
            cabinet_row = db.get(Cabinet, invoice.cabinet_id)
            disabled_keys = set(cabinet_row.disabled_pcg_rules or []) if cabinet_row else set()

            account, label = categorize(
                vendor_name=ocr_result.vendor_name or "",
                description=ocr_result.raw_text[:500],
                custom_rules=custom_rules,
                disabled_keys=disabled_keys,
            )
            if account:
                invoice.pcg_account = account
                invoice.pcg_label = label
                invoice.pcg_source = "auto"

            # Flag for human review if confidence is low or fields are missing
            needs_review = (
                ocr_result.confidence < 0.7
                or invoice.amount_ttc is None
                or invoice.invoice_date is None
            )
            invoice.status = InvoiceStatus.NEEDS_REVIEW if needs_review else InvoiceStatus.VALIDATED
            db.commit()

            logger.info("OCR completed for invoice %s — confidence=%.2f", invoice_id, ocr_result.confidence)
            return {"invoice_id": invoice_id, "status": invoice.status, "confidence": ocr_result.confidence}

        except Exception as exc:
            invoice.status = InvoiceStatus.NEEDS_REVIEW
            invoice.ocr_error = str(exc)
            db.commit()
            logger.exception("OCR failed for invoice %s", invoice_id)
            raise self.retry(exc=exc)
