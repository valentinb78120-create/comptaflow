"""Tests unitaires des exports CSV EBP / Sage 50."""
import uuid
from datetime import date
from decimal import Decimal

from app.models.invoice import Invoice
from app.services.exporter import export_ebp, export_sage50


def make_invoice(**overrides) -> Invoice:
    """Construit une Invoice en mémoire (non persistée) pour les tests."""
    defaults = dict(
        id=uuid.uuid4(),
        cabinet_id=uuid.uuid4(),
        original_filename="facture.pdf",
        storage_path="/tmp/facture.pdf",
        file_mime_type="application/pdf",
        vendor_name="EDF",
        invoice_number="FAC-2026-001",
        invoice_date=date(2026, 6, 1),
        amount_ht=Decimal("100.00"),
        amount_tva=Decimal("20.00"),
        amount_ttc=Decimal("120.00"),
        pcg_account="606100",
        pcg_label="Énergie électrique",
    )
    defaults.update(overrides)
    return Invoice(**defaults)


class TestExportEBP:
    def test_header_and_encoding(self):
        data = export_ebp([make_invoice()])
        # UTF-8 BOM pour Excel
        assert data.startswith("﻿".encode("utf-8"))
        text = data.decode("utf-8-sig")
        assert text.splitlines()[0] == "Date;Compte;Libellé;Débit;Crédit;Réf"

    def test_three_balanced_lines_per_invoice(self):
        text = export_ebp([make_invoice()]).decode("utf-8-sig")
        lines = [l for l in text.splitlines() if l][1:]  # sans en-tête
        assert len(lines) == 3

        # débit HT + débit TVA == crédit TTC
        def amounts(line: str) -> tuple[Decimal, Decimal]:
            parts = line.split(";")
            return (Decimal(parts[3].replace(",", ".")), Decimal(parts[4].replace(",", ".")))

        debit_total = sum(amounts(l)[0] for l in lines)
        credit_total = sum(amounts(l)[1] for l in lines)
        assert debit_total == credit_total == Decimal("120.00")

    def test_accounts_in_lines(self):
        text = export_ebp([make_invoice()]).decode("utf-8-sig")
        assert ";606100;" in text       # charge
        assert ";445660;" in text       # TVA déductible
        assert ";401000;" in text       # fournisseur

    def test_date_format_ddmmyyyy(self):
        text = export_ebp([make_invoice()]).decode("utf-8-sig")
        assert "01/06/2026" in text

    def test_french_decimal_separator(self):
        text = export_ebp([make_invoice()]).decode("utf-8-sig")
        assert "120,00" in text
        assert "120.00" not in text

    def test_missing_amounts_default_to_zero(self):
        inv = make_invoice(amount_ht=None, amount_tva=None, amount_ttc=None)
        text = export_ebp([inv]).decode("utf-8-sig")
        assert "0,00" in text  # ne crashe pas

    def test_default_account_when_uncategorized(self):
        inv = make_invoice(pcg_account=None, pcg_label=None)
        text = export_ebp([inv]).decode("utf-8-sig")
        assert ";607000;" in text  # compte achat par défaut

    def test_multiple_invoices(self):
        text = export_ebp([make_invoice(), make_invoice(), make_invoice()]).decode("utf-8-sig")
        lines = [l for l in text.splitlines() if l][1:]
        assert len(lines) == 9  # 3 lignes × 3 factures


class TestExportSage50:
    def test_encoding_latin1_and_separator(self):
        data = export_sage50([make_invoice()])
        text = data.decode("latin-1")
        assert text.splitlines()[0] == "Date,Compte,Libellé,Débit,Crédit,Référence"

    def test_dot_decimal_separator(self):
        text = export_sage50([make_invoice()]).decode("latin-1")
        assert "120.00" in text

    def test_non_latin1_chars_replaced_not_crash(self):
        inv = make_invoice(vendor_name="Fournisseur 中文 €")
        data = export_sage50([inv])  # ne doit pas lever UnicodeEncodeError
        assert isinstance(data, bytes)
