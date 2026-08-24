"""
Stripe billing service.

Toutes les fonctions se dégradent proprement quand STRIPE_SECRET_KEY n'est
pas configurée (mode dev / trial only) : elles lèvent StripeNotConfiguredError
que les routes traduisent en 503 avec un message explicite.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.config import get_settings
from app.models.cabinet import Cabinet

logger = logging.getLogger(__name__)
settings = get_settings()


class StripeNotConfiguredError(RuntimeError):
    """STRIPE_SECRET_KEY absente — facturation désactivée."""


def _stripe():
    """Import paresseux du SDK, configuré avec la clé secrète."""
    if not settings.stripe_secret_key:
        raise StripeNotConfiguredError("STRIPE_SECRET_KEY non configurée")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe


def trial_active(cabinet: Cabinet) -> bool:
    """Le trial gratuit du cabinet est-il encore en cours ?"""
    if cabinet.trial_ends_at is None:
        return False
    ends = cabinet.trial_ends_at
    if ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    return ends > datetime.now(timezone.utc)


def has_access(cabinet: Cabinet) -> bool:
    """Le cabinet peut-il utiliser l'application (abonné OU en trial) ?"""
    return cabinet.subscription_active or trial_active(cabinet)


def create_checkout_session(
    cabinet: Cabinet, success_url: str, cancel_url: str, plan: str = "cabinet"
) -> str:
    """
    Crée une session Stripe Checkout pour l'abonnement mensuel du *plan* choisi.
    Retourne l'URL de paiement vers laquelle rediriger l'utilisateur.
    """
    stripe = _stripe()
    price_id = settings.stripe_price_for_plan(plan)
    if not price_id:
        raise StripeNotConfiguredError(f"Price ID Stripe non configuré pour le plan {plan}")

    # Réutilise le customer Stripe existant, sinon en crée un
    customer_id = cabinet.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=cabinet.email,
            name=cabinet.name,
            metadata={"cabinet_id": str(cabinet.id)},
        )
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"cabinet_id": str(cabinet.id), "plan": plan},
    )
    return session.url


def create_portal_session(cabinet: Cabinet, return_url: str) -> str:
    """Ouvre le portail client Stripe (gestion CB, annulation, factures)."""
    stripe = _stripe()
    if not cabinet.stripe_customer_id:
        raise StripeNotConfiguredError("Cabinet sans customer Stripe — souscrire d'abord")

    session = stripe.billing_portal.Session.create(
        customer=cabinet.stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def verify_webhook(payload: bytes, signature: str) -> dict:
    """Vérifie la signature du webhook Stripe et retourne l'événement."""
    stripe = _stripe()
    if not settings.stripe_webhook_secret:
        raise StripeNotConfiguredError("STRIPE_WEBHOOK_SECRET non configuré")
    return stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
