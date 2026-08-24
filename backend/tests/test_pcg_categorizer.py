"""Tests unitaires du moteur de catégorisation PCG."""
import pytest

from app.services.pcg_categorizer import categorize, get_all_rules


class TestCategorize:
    @pytest.mark.parametrize(
        ("vendor", "expected_account"),
        [
            ("EDF", "606100"),
            ("Engie SA", "606100"),
            ("TOTAL ENERGIES", "606100"),
            ("GRDF", "606200"),
            ("Veolia Eau", "606300"),
            ("Orange Business", "626000"),
            ("FREE PRO", "626000"),
            ("AXA Assurances", "616000"),
            ("SNCF Connect", "625100"),
            ("Uber France", "625200"),
            ("Microsoft Ireland", "618500"),
            ("Adecco France", "621100"),
            ("BNP Paribas frais", "627000"),
        ],
    )
    def test_known_vendors(self, vendor: str, expected_account: str):
        account, label = categorize(vendor)
        assert account == expected_account
        assert label  # libellé non vide

    def test_keyword_in_description(self):
        """Le mot-clé peut venir de la description, pas seulement du fournisseur."""
        account, _ = categorize("SCI Les Tilleuls", "Loyer bureaux mars 2026")
        assert account == "613000"

    def test_case_insensitive(self):
        assert categorize("edf")[0] == categorize("EDF")[0] == "606100"

    def test_unknown_vendor_returns_none(self):
        account, label = categorize("Fournisseur Inconnu XYZ")
        assert account is None
        assert label is None

    def test_empty_input(self):
        assert categorize("") == (None, None)

    def test_first_match_wins(self):
        """'EDF' apparaît avant les règles génériques — l'ordre est respecté."""
        account, _ = categorize("EDF entretien chaudière")
        assert account == "606100"  # EDF (première règle), pas 615000 (entretien)


class TestRules:
    def test_rules_are_exposed(self):
        rules = get_all_rules()
        assert len(rules) >= 20
        assert all({"keywords", "account", "label"} <= set(r) for r in rules)

    def test_accounts_look_like_pcg(self):
        for rule in get_all_rules():
            assert rule["account"].isdigit() and len(rule["account"]) >= 6, rule
