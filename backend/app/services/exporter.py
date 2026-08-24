"""
CSV export service — generates EBP Compta and Sage 50 compatible files.

EBP Compta format:
  Date;Compte;Libellé;Débit;Crédit;Réf
  Encoding: UTF-8-BOM, separator: semicolon

Sage 50 format:
  Date,Compte,Libellé,Débit,Crédit,Référence
  Encoding: Latin-1 (ISO-8859-1), separator: comma (Sage 50 FR default)
"""
from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

from app.models.invoice import Invoice


def _fmt_amount(value: Decimal | None) -> str:
    """Format a Decimal as a French decimal string (comma separator)."""
    if value is None:
        return "0,00"
    return f"{value:.2f}".replace(".", ",")


def _fmt_date_ebp(d: date | None) -> str:
    """EBP expects DD/MM/YYYY."""
    return d.strftime("%d/%m/%Y") if d else ""


def _build_ebp_rows(invoice: Invoice) -> list[list[str]]:
    """
    Return journal entry rows in EBP Compta format.

    A standard purchase invoice creates:
      - 1 debit line on the expense account (PCG)
      - 1 debit line on TVA recoverable (445660)
      - 1 credit line on supplier payable (401000)
    """
    ref = invoice.invoice_number or str(invoice.id)[:8].upper()
    d = _fmt_date_ebp(invoice.invoice_date)
    vendor = (invoice.vendor_name or "FOURNISSEUR")[:35]
    pcg = invoice.pcg_account or "607000"
    label_ht = f"{vendor} - {invoice.pcg_label or 'Achat'}"
    label_tva = f"TVA déductible {vendor}"
    label_ttc = f"Fournisseur {vendor}"

    ht = invoice.amount_ht or Decimal("0")
    tva = invoice.amount_tva or Decimal("0")
    ttc = invoice.amount_ttc or (ht + tva)

    rows = [
        [d, pcg, label_ht[:50], _fmt_amount(ht), "0,00", ref],
        [d, "445660", label_tva[:50], _fmt_amount(tva), "0,00", ref],
        [d, "401000", label_ttc[:50], "0,00", _fmt_amount(ttc), ref],
    ]
    return rows


def export_ebp(invoices: list[Invoice]) -> bytes:
    """
    Generate an EBP Compta CSV file for *invoices*.

    Returns UTF-8-BOM encoded bytes ready for download.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(["Date", "Compte", "Libellé", "Débit", "Crédit", "Réf"])

    for inv in invoices:
        for row in _build_ebp_rows(inv):
            writer.writerow(row)

    # UTF-8 BOM so Excel opens the file correctly
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _fmt_date_fec(d: date | None) -> str:
    """Le FEC exige AAAAMMJJ."""
    return d.strftime("%Y%m%d") if d else ""


# Les 18 colonnes obligatoires du FEC (art. A47 A-1 du LPF)
FEC_HEADERS = [
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate",
    "CompteNum", "CompteLib", "CompAuxNum", "CompAuxLib",
    "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit",
    "EcritureLet", "DateLet", "ValidDate", "Montantdevise", "Idevise",
]


def export_fec(invoices: list[Invoice]) -> bytes:
    """
    Génère un FEC (Fichier des Écritures Comptables) pour *invoices*.

    Format DGFiP : 18 colonnes séparées par tabulation, dates AAAAMMJJ,
    décimales à virgule, encodage ISO-8859-15. Journal achats "AC".
    Chaque facture produit 3 lignes équilibrées (charge / TVA / fournisseur).
    """
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", quoting=csv.QUOTE_NONE, lineterminator="\r\n")
    writer.writerow(FEC_HEADERS)

    for num, inv in enumerate(invoices, start=1):
        ref = (inv.invoice_number or str(inv.id)[:8].upper()).replace("\t", " ")
        ecriture_date = _fmt_date_fec(inv.invoice_date)
        vendor = (inv.vendor_name or "FOURNISSEUR").replace("\t", " ")[:60]
        pcg = inv.pcg_account or "607000"
        charge_lib = (inv.pcg_label or "Achats de marchandises")[:60]

        ht = inv.amount_ht or Decimal("0")
        tva = inv.amount_tva or Decimal("0")
        ttc = inv.amount_ttc or (ht + tva)

        def row(compte: str, compte_lib: str, lib: str, debit: Decimal, credit: Decimal,
                aux_num: str = "", aux_lib: str = "") -> list[str]:
            return [
                "AC", "Achats", str(num), ecriture_date,
                compte, compte_lib, aux_num, aux_lib,
                ref, ecriture_date, lib[:100],
                _fmt_amount(debit), _fmt_amount(credit),
                "", "", ecriture_date, "", "",
            ]

        writer.writerow(row(pcg, charge_lib, f"{vendor} - {charge_lib}", ht, Decimal("0")))
        writer.writerow(row("445660", "TVA déductible sur ABS", f"TVA {vendor}", tva, Decimal("0")))
        writer.writerow(row("401000", "Fournisseurs", f"Facture {vendor}", Decimal("0"), ttc,
                            aux_num="401" + ref[:14], aux_lib=vendor))

    return buf.getvalue().encode("iso-8859-15", errors="replace")


def fec_filename(siren: str | None, closing: date | None = None) -> str:
    """
    Nom réglementaire : SIRENFECAAAAMMJJ.txt (AAAAMMJJ = date de clôture).
    SIREN par défaut 000000000 si le cabinet n'a pas renseigné son SIRET.
    """
    siren_digits = (siren or "")[:9]
    if len(siren_digits) != 9 or not siren_digits.isdigit():
        siren_digits = "000000000"
    closing = closing or date.today()
    return f"{siren_digits}FEC{closing.strftime('%Y%m%d')}.txt"


def export_sage50(invoices: list[Invoice]) -> bytes:
    """
    Generate a Sage 50 Comptabilité CSV file for *invoices*.

    Returns Latin-1 encoded bytes.  Characters not representable in Latin-1
    are replaced with '?' to avoid encode errors.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(["Date", "Compte", "Libellé", "Débit", "Crédit", "Référence"])

    for inv in invoices:
        for row in _build_ebp_rows(inv):
            # Sage uses dot as decimal separator
            row[3] = row[3].replace(",", ".")
            row[4] = row[4].replace(",", ".")
            writer.writerow(row)

    return buf.getvalue().encode("latin-1", errors="replace")
