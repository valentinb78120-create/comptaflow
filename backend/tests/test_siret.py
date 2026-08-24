"""Tests de la validation SIRET (Luhn + exception La Poste)."""
import pytest

from app.services.siret import validate_siret


class TestValidateSiret:
    @pytest.mark.parametrize("siret", [
        "73282932000074",   # exemple INSEE valide
        "55208131766522",   # autre SIRET Luhn-valide
        "732 829 320 00074",  # avec espaces
    ])
    def test_sirets_valides(self, siret):
        assert validate_siret(siret) is True

    @pytest.mark.parametrize("siret", [
        "73282932000075",   # mauvaise clé Luhn
        "12345678901234",   # Luhn KO
        "1234567890123",    # 13 chiffres
        "123456789012345",  # 15 chiffres
        "7328293200007A",   # lettre
        "",                 # vide
    ])
    def test_sirets_invalides(self, siret):
        assert validate_siret(siret) is False

    def test_la_poste_somme_multiple_de_5(self):
        # SIREN La Poste 356000000 : somme simple des chiffres % 5 == 0
        # somme(356000000) = 14 ; NIC 00001 → 15, multiple de 5 → valide
        assert validate_siret("35600000000001") is True

    def test_la_poste_invalide(self):
        assert validate_siret("35600000000002") is False
