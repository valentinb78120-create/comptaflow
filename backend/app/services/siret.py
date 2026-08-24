"""
Validation de SIRET français (14 chiffres, somme de Luhn).

Cas particulier : les établissements de La Poste (SIREN 356000000)
ne suivent pas Luhn — la somme simple des chiffres doit être un multiple de 5.
"""
from __future__ import annotations

import re


def validate_siret(siret: str) -> bool:
    """Retourne True si *siret* est un SIRET français structurellement valide."""
    cleaned = re.sub(r"\s", "", siret)
    if not re.fullmatch(r"\d{14}", cleaned):
        return False

    # Exception La Poste
    if cleaned.startswith("356000000"):
        return sum(int(d) for d in cleaned) % 5 == 0

    return _luhn_ok(cleaned)


def _luhn_ok(digits: str) -> bool:
    """Somme de Luhn : doubler un chiffre sur deux depuis la droite."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0
