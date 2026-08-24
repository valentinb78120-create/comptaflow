"""Tests du parsing de l'annotation structurée Mistral (document_annotation)."""
import json
from datetime import date
from decimal import Decimal

from app.services.mistral_ocr import _parse_document_annotation, _parse_mistral_response


def make_annotation(**fields) -> dict:
    base = {
        "vendor_name": "EDF",
        "invoice_number": "F-001",
        "invoice_date": "2026-06-01",
        "due_date": None,
        "amount_ht": 100.0,
        "amount_tva": 20.0,
        "amount_ttc": 120.0,
        "tva_rate": 20,
    }
    base.update(fields)
    return {"document_annotation": json.dumps(base), "pages": []}


class TestDocumentAnnotation:
    def test_annotation_complete(self):
        r = _parse_document_annotation(make_annotation())
        assert r is not None
        assert r.vendor_name == "EDF"
        assert r.invoice_date == date(2026, 6, 1)
        assert r.amount_ttc == Decimal("120.0")
        assert r.tva_rate == Decimal("20")
        # Bonus structuré, mais jamais 100%
        assert r.confidence == 0.95

    def test_annotation_absente_retourne_none(self):
        assert _parse_document_annotation({"pages": []}) is None

    def test_annotation_json_invalide(self):
        assert _parse_document_annotation({"document_annotation": "{pas du json"}) is None

    def test_champs_null_acceptes(self):
        raw = make_annotation(vendor_name=None, amount_ttc=None)
        r = _parse_document_annotation(raw)
        assert r is not None
        assert r.vendor_name is None
        assert r.amount_ttc is None
        assert r.confidence < 0.7  # ira en revue humaine

    def test_date_malformee_ignoree(self):
        r = _parse_document_annotation(make_annotation(invoice_date="pas-une-date"))
        assert r is not None
        assert r.invoice_date is None

    def test_priorite_annotation_sur_regex(self):
        """Quand l'annotation existe, les regex ne sont pas utilisées."""
        raw = make_annotation(vendor_name="Fournisseur Annoté")
        raw["pages"] = [{"markdown": "FACTURE N° AUTRE-999\nMontant TTC : 555,00 €"}]
        r = _parse_mistral_response(raw)
        assert r.vendor_name == "Fournisseur Annoté"
        assert r.amount_ttc == Decimal("120.0")  # de l'annotation, pas 555

    def test_fallback_regex_sans_annotation(self):
        raw = {"pages": [{"markdown": "FACTURE N° REG-1\nMontant TTC : 99,00"}]}
        r = _parse_mistral_response(raw)
        assert r.invoice_number == "REG-1"
        assert r.amount_ttc == Decimal("99.00")
