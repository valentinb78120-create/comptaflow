"""
Back-office administrateur — réservé aux comptes is_admin.

GET  /admin/stats                          — KPIs globaux de la plateforme
GET  /admin/cabinets                       — tous les cabinets + volumétrie
POST /admin/cabinets/{id}/extend-trial     — prolonger l'essai de N jours
POST /admin/cabinets/{id}/toggle-subscription — activer/couper l'abonnement à la main
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.cabinet import Cabinet
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.cabinet import CabinetOut

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],  # toutes les routes exigent un admin
)


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------

class PlatformStats(BaseModel):
    cabinets_total: int
    cabinets_subscribed: int
    cabinets_in_trial: int
    invoices_total: int
    invoices_last_7d: int
    invoices_by_status: dict[str, int]


class AdminCabinetRow(CabinetOut):
    invoice_count: int = 0


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=PlatformStats)
async def platform_stats(db: AsyncSession = Depends(get_db)) -> PlatformStats:
    """KPIs globaux : cabinets, abonnements, volumétrie factures."""
    now = datetime.now(timezone.utc)

    cabinets_total = (await db.execute(select(func.count(Cabinet.id)))).scalar_one()
    cabinets_subscribed = (
        await db.execute(select(func.count(Cabinet.id)).where(Cabinet.subscription_active.is_(True)))
    ).scalar_one()
    cabinets_in_trial = (
        await db.execute(
            select(func.count(Cabinet.id)).where(
                Cabinet.subscription_active.is_(False),
                Cabinet.trial_ends_at > now,
            )
        )
    ).scalar_one()

    invoices_total = (await db.execute(select(func.count(Invoice.id)))).scalar_one()
    invoices_last_7d = (
        await db.execute(
            select(func.count(Invoice.id)).where(Invoice.created_at > now - timedelta(days=7))
        )
    ).scalar_one()

    by_status_rows = (
        await db.execute(select(Invoice.status, func.count(Invoice.id)).group_by(Invoice.status))
    ).all()
    invoices_by_status = {str(s): c for s, c in by_status_rows}
    # Statuts absents → 0 (affichage stable côté UI)
    for st in InvoiceStatus:
        invoices_by_status.setdefault(st.value, 0)

    return PlatformStats(
        cabinets_total=cabinets_total,
        cabinets_subscribed=cabinets_subscribed,
        cabinets_in_trial=cabinets_in_trial,
        invoices_total=invoices_total,
        invoices_last_7d=invoices_last_7d,
        invoices_by_status=invoices_by_status,
    )


# ---------------------------------------------------------------------------
# Cabinets
# ---------------------------------------------------------------------------

@router.get("/cabinets", response_model=list[AdminCabinetRow])
async def list_all_cabinets(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[AdminCabinetRow]:
    """Tous les cabinets avec leur nombre de factures, plus récents d'abord."""
    rows = (
        await db.execute(
            select(Cabinet, func.count(Invoice.id))
            .outerjoin(Invoice, Invoice.cabinet_id == Cabinet.id)
            .group_by(Cabinet.id)
            .order_by(Cabinet.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [
        AdminCabinetRow(**CabinetOut.model_validate(cab).model_dump(), invoice_count=count)
        for cab, count in rows
    ]


@router.post("/cabinets/{cabinet_id}/extend-trial", response_model=CabinetOut)
async def extend_trial(
    cabinet_id: uuid.UUID,
    days: int = Query(14, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> Cabinet:
    """Prolonge (ou réactive) la période d'essai de *days* jours à partir de maintenant."""
    cabinet = await db.get(Cabinet, cabinet_id)
    if cabinet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable")

    base = datetime.now(timezone.utc)
    current = cabinet.trial_ends_at
    if current is not None:
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        base = max(base, current)
    cabinet.trial_ends_at = base + timedelta(days=days)
    await db.commit()
    await db.refresh(cabinet)
    return cabinet


@router.post("/cabinets/{cabinet_id}/set-plan", response_model=CabinetOut)
async def set_plan(
    cabinet_id: uuid.UUID,
    plan: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Cabinet:
    """Change le plan tarifaire d'un cabinet (dépannage, offres spéciales, devis Illimité)."""
    from app.core.plans import is_valid_plan

    if not is_valid_plan(plan):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan inconnu")

    cabinet = await db.get(Cabinet, cabinet_id)
    if cabinet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable")

    cabinet.plan = plan
    await db.commit()
    await db.refresh(cabinet)
    return cabinet


@router.post("/cabinets/{cabinet_id}/toggle-subscription", response_model=CabinetOut)
async def toggle_subscription(
    cabinet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Cabinet:
    """Bascule manuelle de l'abonnement (dépannage, offre gracieuse, partenaires)."""
    cabinet = await db.get(Cabinet, cabinet_id)
    if cabinet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable")

    cabinet.subscription_active = not cabinet.subscription_active
    await db.commit()
    await db.refresh(cabinet)
    return cabinet
