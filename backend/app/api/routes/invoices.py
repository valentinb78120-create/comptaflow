"""
Invoice API routes.

POST   /invoices/upload          — upload a file, queue OCR
GET    /invoices/{id}            — fetch invoice with status
PATCH  /invoices/{id}            — human correction
POST   /invoices/{id}/export     — download EBP or Sage CSV
GET    /invoices/                — list invoices for a cabinet
"""
import hashlib
import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_token_cabinet_id, resolve_cabinet_id
from app.core.config import get_settings
from app.core.database import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoicePatch, InvoiceOut, InvoiceUploadResponse
from app.services.exporter import export_ebp, export_fec, export_sage50, fec_filename

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/invoices", tags=["invoices"])

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/tiff", "image/webp"}
MAX_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024


async def monthly_invoice_count(db: AsyncSession, cabinet_id: uuid.UUID) -> int:
    """Nombre de factures uploadées par le cabinet depuis le 1er du mois (UTC)."""
    from sqlalchemy import func

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.cabinet_id == cabinet_id,
            Invoice.created_at >= month_start,
        )
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=InvoiceUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_invoice(
    file: UploadFile = File(...),
    cabinet_id: uuid.UUID | None = Form(None),
    token_cabinet_id: uuid.UUID | None = Depends(get_token_cabinet_id),
    db: AsyncSession = Depends(get_db),
) -> InvoiceUploadResponse:
    """
    Accept a PDF/image upload, persist it to disk, create an Invoice record,
    and dispatch the OCR Celery task asynchronously.

    Le cabinet vient du Bearer token (connecté) ou du champ cabinet_id (démo).
    """
    cabinet_id = resolve_cabinet_id(cabinet_id, token_cabinet_id)

    # Rate limit : 30 uploads / minute / cabinet
    from app.core.ratelimit import check_rate_limit
    if not check_rate_limit(f"upload:{cabinet_id}", max_calls=30, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop d'uploads — réessayez dans une minute",
        )

    # Validate mime type
    detected_mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Format non supporté: {detected_mime}. Formats acceptés: PDF, JPG, PNG",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.max_upload_size_mb} Mo)",
        )

    # Contrôle d'accès : trial expiré + pas d'abonnement → 402 (si activé)
    from app.models.cabinet import Cabinet

    cabinet = await db.get(Cabinet, cabinet_id)
    if cabinet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable")

    if settings.enforce_subscription:
        from app.services.billing import has_access

        if not has_access(cabinet):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Période d'essai terminée — souscrivez pour continuer (dès 29 €/mois)",
            )

    # Quota mensuel du plan (toujours appliqué — c'est le modèle économique)
    from app.core.plans import get_plan, quota_exceeded

    used = await monthly_invoice_count(db, cabinet_id)
    if quota_exceeded(cabinet.plan, used):
        plan_def = get_plan(cabinet.plan)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Quota mensuel atteint ({plan_def['monthly_invoices']} factures "
                f"sur le plan {plan_def['label']}) — passez au plan supérieur dans Réglages"
            ),
        )

    # Détection de doublon : même contenu déjà uploadé par ce cabinet
    file_hash = hashlib.sha256(content).hexdigest()
    dup = await db.execute(
        select(Invoice.id).where(
            Invoice.cabinet_id == cabinet_id,
            Invoice.file_hash == file_hash,
        )
    )
    existing_id = dup.scalar_one_or_none()
    if existing_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cette facture a déjà été uploadée (doublon de {existing_id})",
        )

    # Persist file
    upload_dir = Path(settings.upload_dir) / str(cabinet_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    invoice_id = uuid.uuid4()
    suffix = Path(file.filename or "file").suffix
    storage_path = upload_dir / f"{invoice_id}{suffix}"
    storage_path.write_bytes(content)

    # Create DB record
    invoice = Invoice(
        id=invoice_id,
        cabinet_id=cabinet_id,
        original_filename=file.filename or "upload",
        storage_path=str(storage_path),
        file_mime_type=detected_mime,
        file_hash=file_hash,
        status=InvoiceStatus.PENDING,
    )
    db.add(invoice)
    await db.flush()

    # Dispatch async OCR task
    try:
        from app.workers.celery_app import process_invoice_ocr
        task = process_invoice_ocr.delay(str(invoice_id))
        invoice.celery_task_id = task.id
    except Exception as exc:
        logger.warning("Could not queue OCR task: %s", exc)

    await db.commit()
    logger.info("Invoice %s uploaded by cabinet %s", invoice_id, cabinet_id)

    return InvoiceUploadResponse(
        id=invoice_id,
        status=InvoiceStatus.PENDING,
        message="Facture reçue, traitement OCR en cours",
    )


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[InvoiceOut])
async def list_invoices(
    cabinet_id: uuid.UUID | None = Query(None),
    status_filter: InvoiceStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    token_cabinet_id: uuid.UUID | None = Depends(get_token_cabinet_id),
    db: AsyncSession = Depends(get_db),
) -> list[Invoice]:
    """Return invoices for a cabinet, optionally filtered by status."""
    cabinet_id = resolve_cabinet_id(cabinet_id, token_cabinet_id)
    q = (
        select(Invoice)
        .where(Invoice.cabinet_id == cabinet_id)
        .options(selectinload(Invoice.line_items))
        .order_by(Invoice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status_filter:
        q = q.where(Invoice.status == status_filter)

    result = await db.execute(q)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Get single invoice
# ---------------------------------------------------------------------------

@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Invoice:
    """Return a single invoice with its line items and current OCR status."""
    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.line_items))
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    return invoice


# ---------------------------------------------------------------------------
# Reprocess (relancer l'OCR)
# ---------------------------------------------------------------------------

@router.post("/{invoice_id}/reprocess", response_model=InvoiceUploadResponse)
async def reprocess_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceUploadResponse:
    """
    Relance le job OCR sur une facture existante (ex: après configuration
    de la clé Mistral, ou si le premier passage a échoué).
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")

    if not Path(invoice.storage_path).is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Le fichier original n'existe plus sur le serveur",
        )

    invoice.status = InvoiceStatus.PENDING
    invoice.ocr_error = None

    try:
        from app.workers.celery_app import process_invoice_ocr
        task = process_invoice_ocr.delay(str(invoice_id))
        invoice.celery_task_id = task.id
    except Exception as exc:
        logger.warning("Impossible de relancer le job OCR: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File de traitement indisponible, réessayez",
        )

    await db.commit()
    return InvoiceUploadResponse(
        id=invoice_id,
        status=InvoiceStatus.PENDING,
        message="OCR relancé",
    )


# ---------------------------------------------------------------------------
# Serve original file (preview in validation UI)
# ---------------------------------------------------------------------------

@router.get("/{invoice_id}/file")
async def get_invoice_file(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Stream the original uploaded file (PDF/image) for in-browser preview."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")

    file_path = Path(invoice.storage_path)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur")

    return FileResponse(
        path=file_path,
        media_type=invoice.file_mime_type,
        filename=invoice.original_filename,
        content_disposition_type="inline",
    )


# ---------------------------------------------------------------------------
# Patch (human correction)
# ---------------------------------------------------------------------------

@router.patch("/{invoice_id}", response_model=InvoiceOut)
async def patch_invoice(
    invoice_id: uuid.UUID,
    payload: InvoicePatch,
    db: AsyncSession = Depends(get_db),
) -> Invoice:
    """
    Allow the user to correct any field extracted by OCR.
    Sets pcg_source='manual' when the PCG account is explicitly provided.
    Transitions status to VALIDATED.
    """
    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.line_items))
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")

    update_data = payload.model_dump(exclude_none=True)

    if "pcg_account" in update_data:
        invoice.pcg_source = "manual"

    for field_name, value in update_data.items():
        setattr(invoice, field_name, value)

    invoice.status = InvoiceStatus.VALIDATED
    await db.commit()
    await db.refresh(invoice)
    return invoice


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.api_route("/{invoice_id}/export", methods=["GET", "POST"])
async def export_invoice(
    invoice_id: uuid.UUID,
    format: str = Query("ebp", pattern="^(ebp|sage50)$"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Generate and download a CSV export for *invoice_id*.

    ?format=ebp    → EBP Compta (UTF-8-BOM, semicolon)
    ?format=sage50 → Sage 50 Comptabilité (Latin-1, comma)
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")

    if invoice.status not in (InvoiceStatus.VALIDATED, InvoiceStatus.EXPORTED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La facture doit être validée avant export",
        )

    if format == "ebp":
        csv_bytes = export_ebp([invoice])
        media_type = "text/csv; charset=utf-8"
        filename = f"export_ebp_{invoice_id}.csv"
    else:
        csv_bytes = export_sage50([invoice])
        media_type = "text/csv; charset=latin-1"
        filename = f"export_sage50_{invoice_id}.csv"

    invoice.status = InvoiceStatus.EXPORTED
    await db.commit()

    return Response(
        content=csv_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Bulk export
# ---------------------------------------------------------------------------

@router.api_route("/export/bulk", methods=["GET", "POST"])
async def export_bulk(
    cabinet_id: uuid.UUID | None = Query(None),
    format: str = Query("ebp", pattern="^(ebp|sage50|fec)$"),
    token_cabinet_id: uuid.UUID | None = Depends(get_token_cabinet_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export all validated invoices: CSV EBP/Sage 50 ou FEC réglementaire."""
    cabinet_id = resolve_cabinet_id(cabinet_id, token_cabinet_id)
    result = await db.execute(
        select(Invoice).where(
            Invoice.cabinet_id == cabinet_id,
            Invoice.status.in_([InvoiceStatus.VALIDATED, InvoiceStatus.EXPORTED]),
        )
    )
    invoices = list(result.scalars().all())

    if not invoices:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune facture validée à exporter")

    if format == "ebp":
        csv_bytes = export_ebp(invoices)
        media_type = "text/csv; charset=utf-8"
        filename = f"export_ebp_bulk_{cabinet_id}.csv"
    elif format == "fec":
        from app.models.cabinet import Cabinet
        cabinet = await db.get(Cabinet, cabinet_id)
        csv_bytes = export_fec(invoices)
        media_type = "text/plain; charset=iso-8859-15"
        filename = fec_filename(cabinet.siret if cabinet else None)
    else:
        csv_bytes = export_sage50(invoices)
        media_type = "text/csv; charset=latin-1"
        filename = f"export_sage50_bulk_{cabinet_id}.csv"

    return Response(
        content=csv_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
