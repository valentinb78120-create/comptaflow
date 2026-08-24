"""Tests unitaires du parsing de texte OCR (extracteurs regex)."""
from datetime import date
from decimal import Decimal

from app.services.mistral_ocr import parse_invoice_text, _parse_mistral_response

FACTURE_EDF = """
EDF Entreprises
Direction Commerce

FACTURE N° 2026-04-12345
Date de facture : 15/04/2026
Date d'échéance : 15/05/2026

Fourniture d'électricité — avril 2026

Montant HT : 250,00 €
TVA 20% : 50,00 €
Montant TTC : 300,00 €
"""

FACTURE_MINIMALE = """
SARL Plombiers Réunis
Facture n° PR-889
12/03/2026
Total à payer : 1 450,50 EUR
"""


class TestParseInvoiceText:
    def test_facture_complete(self):
        r = parse_invoice_text(FACTURE_EDF)
        assert r.invoice_number == "2026-04-12345"
        assert r.invoice_date == date(2026, 4, 15)
        assert r.due_date == date(2026, 5, 15)
        assert r.amount_ht == Decimal("250.00")
        assert r.amount_tva == Decimal("50.00")
        assert r.amount_ttc == Decimal("300.00")
        assert r.tva_rate == Decimal("20")
        assert r.confidence > 0.6

    def test_facture_minimale(self):
        r = parse_invoice_text(FACTURE_MINIMALE)
        assert r.invoice_number == "PR-889"
        assert r.invoice_date == date(2026, 3, 12)
        # "1 450,50" avec espace de milliers
        assert r.amount_ttc == Decimal("1450.50")

    def test_texte_vide(self):
        r = parse_invoice_text("")
        assert r.confidence == 0.0
        assert r.vendor_name is None
        assert r.amount_ttc is None

    def test_texte_sans_facture(self):
        r = parse_invoice_text("Ceci est un document quelconque sans aucune info de facturation.")
        assert r.amount_ttc is None
        assert r.confidence < 0.7  # doit partir en revue humaine

    def test_montants_format_anglais(self):
        r = parse_invoice_text("Total HT: 99.90\nTVA: 19.98\nTotal TTC: 119.88")
        assert r.amount_ht == Decimal("99.90")
        assert r.amount_ttc == Decimal("119.88")

    def test_date_invalide_ignoree(self):
        # 45/13/2026 n'est pas une date — ne doit pas lever d'exception
        r = parse_invoice_text("Date de facture : 45/13/2026")
        assert r.invoice_date is None


class TestParseMistralResponse:
    def test_pages_markdown_jointes(self):
        raw = {
            "pages": [
                {"markdown": "FACTURE N° ABC-1\nDate de facture : 01/02/2026"},
                {"markdown": "Montant TTC : 42,00 €"},
            ]
        }
        r = _parse_mistral_response(raw)
        assert r.invoice_number == "ABC-1"
        assert r.amount_ttc == Decimal("42.00")
        assert r.raw_response is raw

    def test_reponse_vide(self):
        r = _parse_mistral_response({})
        assert r.confidence == 0.0
