"""
Grille tarifaire ComptaFlow — source de vérité unique des plans.

Le quota est un nombre de factures uploadées par mois calendaire.
None = illimité. Le plan est stocké sur Cabinet.plan ; les cabinets
existants et les nouveaux comptes démarrent sur le plan "cabinet"
(c'est aussi le plan couvert par le trial 14 jours).
"""
from __future__ import annotations

PLANS: dict[str, dict] = {
    "decouverte": {
        "label": "Découverte",
        "price_eur": 29,
        "monthly_invoices": 100,
    },
    "cabinet": {
        "label": "Cabinet",
        "price_eur": 79,
        "monthly_invoices": 1000,
    },
    "cabinet_plus": {
        "label": "Cabinet+",
        "price_eur": 199,
        "monthly_invoices": 5000,
    },
    "illimite": {
        "label": "Illimité",
        "price_eur": None,  # sur devis
        "monthly_invoices": None,
    },
}

DEFAULT_PLAN = "cabinet"


def get_plan(plan_key: str | None) -> dict:
    """Définition du plan ; retombe sur le plan par défaut si inconnu."""
    return PLANS.get(plan_key or DEFAULT_PLAN, PLANS[DEFAULT_PLAN])


def monthly_limit(plan_key: str | None) -> int | None:
    """Quota mensuel de factures du plan (None = illimité)."""
    return get_plan(plan_key)["monthly_invoices"]


def quota_exceeded(plan_key: str | None, used_this_month: int) -> bool:
    """Le cabinet a-t-il épuisé son quota mensuel ?"""
    limit = monthly_limit(plan_key)
    return limit is not None and used_this_month >= limit


def is_valid_plan(plan_key: str) -> bool:
    return plan_key in PLANS
