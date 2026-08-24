"""Tests de l'export FEC (Fichier des Écritures Comptables)."""
from datetime import date
from decimal import Decimal

from app.services.exporter import FEC_HEADERS, export_fec, fec_filename
from tests.test_exporter import make_invoice


class TestExportFEC:
    def test_en_tete_18_colonnes(self):
        text = export_fec([make_invoice()]).decode("iso-8859-15")
        header = text.splitlines()[0].split("\t")
        assert header == FEC_HEADERS
        assert len(header) == 18

    def test_trois_lignes_par_facture_equilibrees(self):
        text = export_fec([make_invoice()]).decode("iso-8859-15")
        lines = [l.split("\t") for l in text.splitlines()[1:] if l]
        assert len(lines) == 3

        i_debit, i_credit = FEC_HEADERS.index("Debit"), FEC_HEADERS.index("Credit")
        debit = sum(Decimal(l[i_debit].replace(",", ".")) for l in lines)
        credit = sum(Decimal(l[i_credit].replace(",", ".")) for l in lines)
        assert debit == credit == Decimal("120.00")

    def test_dates_au_format_aaaammjj(self):
        text = export_fec([make_invoice()]).decode("iso-8859-15")
        ligne = text.splitlines()[1].split("\t")
        assert ligne[FEC_HEADERS.index("EcritureDate")] == "20260601"

    def test_journal_achats(self):
        text = export_fec([make_invoice()]).decode("iso-8859-15")
        ligne = text.splitlines()[1].split("\t")
        assert ligne[0] == "AC"
        assert ligne[1] == "Achats"

    def test_numerotation_sequentielle(self):
        text = export_fec([make_invoice(), make_invoice()]).decode("iso-8859-15")
        nums = {l.split("\t")[2] for l in text.splitlines()[1:] if l}
        assert nums == {"1", "2"}

    def test_compte_auxiliaire_fournisseur(self):
        text = export_fec([make_invoice()]).decode("iso-8859-15")
        ligne_fournisseur = [l for l in text.splitlines()[1:] if l.split("\t")[4] == "401000"][0]
        cols = ligne_fournisseur.split("\t")
        assert cols[FEC_HEADERS.index("CompAuxLib")] == "EDF"

    def test_encodage_iso_8859_15(self):
        inv = make_invoice(vendor_name="Électricité Générale €")
        data = export_fec([inv])  # ne doit pas lever (€ existe en 8859-15)
        assert "Électricité".encode("iso-8859-15") in data


class TestFecFilename:
    def test_avec_siret(self):
        name = fec_filename("73282932000074", closing=date(2026, 12, 31))
        assert name == "732829320FEC20261231.txt"

    def test_sans_siret(self):
        name = fec_filename(None, closing=date(2026, 12, 31))
        assert name == "000000000FEC20261231.txt"

    def test_siret_invalide(self):
        assert fec_filename("ABC", closing=date(2026, 1, 1)).startswith("000000000FEC")
