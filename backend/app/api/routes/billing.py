"""
Billing routes — abonnement Stripe (79 €/mois après trial 14 jours).

GET  /billing/status?cabinet_id=        — état d'accès (trial / abonné / expiré)
POST /billing/checkout-session          — démarre la souscription (URL Stripe)
POST /billing/portal                    — portail client Stripe
POST /billing/webhook                   — événements Stripe (subscription.*)
"""
import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.cabinet import Cabinet
from app.services import billing

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


class BillingStatus(BaseModel):
    cabinet_id: uuid.UUID
    subscription_active: bool
    trial_active: bool
    trial_ends_at: str | None
    has_access: bool
    stripe_configured: bool
    # Plan & quota
    plan: str
    plan_label: str
    plan_price_eur: int | None
    monthly_limit: int | None
    monthly_used: int


class CheckoutRequest(BaseModel):
    cabinet_id: uuid.UUID
    plan: str = "cabinet"
    success_url: str = "http://localhost:5173/dashboard?billing=success"
    cancel_url: str = "http://localhost:5173/dashboard?billing=cancel"


class UrlResponse(BaseModel):
    url: str


async def _get_cabinet(cabinet_id: uuid.UUID, db: AsyncSession) -> Cabinet:
    cabinet = await db.get(Cabinet, cabinet_id)
    if cabinet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable")
    return cabinet


@router.get("/status", response_model=BillingStatus)
async def billing_status(
    cabinet_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> BillingStatus:
    """État d'accès du cabinet : trial/abonnement, plan et consommation du mois."""
    from app.core.config import get_settings
    from app.core.plans import get_plan, monthly_limit
    from app.api.routes.invoices import monthly_invoice_count

    cabinet = await _get_cabinet(cabinet_id, db)
    plan_def = get_plan(cabinet.plan)
    used = await monthly_invoice_count(db, cabinet.id)

    return BillingStatus(
        cabinet_id=cabinet.id,
        subscription_active=cabinet.subscription_active,
        trial_active=billing.trial_active(cabinet),
        trial_ends_at=cabinet.trial_ends_at.isoformat() if cabinet.trial_ends_at else None,
        has_access=billing.has_access(cabinet),
        stripe_configured=bool(get_settings().stripe_secret_key),
        plan=cabinet.plan,
        plan_label=plan_def["label"],
        plan_price_eur=plan_def["price_eur"],
        monthly_limit=monthly_limit(cabinet.plan),
        monthly_used=used,
    )


@router.post("/checkout-session", response_model=UrlResponse)
async def create_checkout(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
) -> UrlResponse:
    """Crée une session Stripe Checkout et retourne son URL."""
    from app.core.plans import is_valid_plan

    if not is_valid_plan(payload.plan) or payload.plan == "illimite":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan inconnu")

    cabinet = await _get_cabinet(payload.cabinet_id, db)
    try:
        url = billing.create_checkout_session(
            cabinet, payload.success_url, payload.cancel_url, plan=payload.plan
        )
    except billing.StripeNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    await db.commit()
    return UrlResponse(url=url)


@router.post("/portal", response_model=UrlResponse)
async def create_portal(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
) -> UrlResponse:
    """Ouvre le portail de gestion d'abonnement Stripe."""
    cabinet = await _get_cabinet(payload.cabinet_id, db)
    try:
        url = billing.create_portal_session(cabinet, payload.success_url)
    except billing.StripeNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return UrlResponse(url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Réception des événements Stripe.
    Gère le cycle de vie de l'abonnement : activation et désactivation.
    """
    payload = await request.body()
    try:
        event = billing.verify_webhook(payload, stripe_signature or "")
    except billing.StripeNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signature webhook invalide")

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata", {})
        cabinet_id = metadata.get("cabinet_id")
        if cabinet_id:
            cabinet = await db.get(Cabinet, uuid.UUID(cabinet_id))
            if cabinet:
                cabinet.stripe_customer_id = obj.get("customer")
                cabinet.stripe_subscription_id = obj.get("subscription")
                cabinet.subscription_active = True
                # Applique le plan souscrit (metadata posée au checkout)
                from app.core.plans import is_valid_plan
                plan = metadata.get("plan")
                if plan and is_valid_plan(plan):
                    cabinet.plan = plan
                await db.commit()
                logger.info("Abonnement %s activé pour le cabinet %s", plan, cabinet_id)

    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        sub_id = obj.get("id")
        result = await db.execute(select(Cabinet).where(Cabinet.stripe_subscription_id == sub_id))
        cabinet = result.scalar_one_or_none()
        if cabinet:
            cabinet.subscription_active = False
            await db.commit()
            logger.info("Abonnement désactivé pour le cabinet %s", cabinet.id)

    elif event_type == "customer.subscription.updated":
        sub_id = obj.get("id")
        result = await db.execute(select(Cabinet).where(Cabinet.stripe_subscription_id == sub_id))
        cabinet = result.scalar_one_or_none()
        if cabinet:
            cabinet.subscription_active = obj.get("status") in ("active", "trialing")
            await db.commit()

    return {"received": True}
