"""Tests de la grille tarifaire et des quotas."""
from app.core.plans import DEFAULT_PLAN, PLANS, get_plan, is_valid_plan, monthly_limit, quota_exceeded


class TestPlans:
    def test_quatre_plans(self):
        assert set(PLANS) == {"decouverte", "cabinet", "cabinet_plus", "illimite"}

    def test_quotas_croissants(self):
        assert monthly_limit("decouverte") == 100
        assert monthly_limit("cabinet") == 1000
        assert monthly_limit("cabinet_plus") == 5000
        assert monthly_limit("illimite") is None

    def test_plan_inconnu_retombe_sur_defaut(self):
        assert get_plan("nimporte-quoi") == PLANS[DEFAULT_PLAN]
        assert get_plan(None) == PLANS[DEFAULT_PLAN]

    def test_prix(self):
        assert get_plan("decouverte")["price_eur"] == 29
        assert get_plan("cabinet")["price_eur"] == 79
        assert get_plan("cabinet_plus")["price_eur"] == 199
        assert get_plan("illimite")["price_eur"] is None  # sur devis


class TestQuota:
    def test_sous_le_quota(self):
        assert quota_exceeded("decouverte", 99) is False

    def test_au_quota(self):
        assert quota_exceeded("decouverte", 100) is True

    def test_illimite_jamais_depasse(self):
        assert quota_exceeded("illimite", 10_000_000) is False

    def test_plan_inconnu_quota_defaut(self):
        assert quota_exceeded("inconnu", 999) is False
        assert quota_exceeded("inconnu", 1000) is True


class TestValidation:
    def test_plans_valides(self):
        for p in PLANS:
            assert is_valid_plan(p)

    def test_plan_invalide(self):
        assert is_valid_plan("gratuit") is False
