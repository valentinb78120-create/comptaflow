"""
Tests d'intégration — parcours API complet contre l'application réelle.

S'exécutent DANS le container api (DB + Redis accessibles) :
    docker compose exec api python -m pytest tests/test_integration_api.py

Marqués `integration` : exclus si la stack ne tourne pas.
"""
import time
import uuid

import httpx
import pytest

BASE = "http://localhost:8000/api/v1"

# PDF minimal valide pour l'upload
PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF"
)


def stack_up() -> bool:
    try:
        return httpx.get("http://localhost:8000/health", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not stack_up(), reason="API non démarrée")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        yield c


@pytest.fixture(scope="module")
def cabinet_id(client) -> str:
    r = client.post(
        "/cabinets/",
        json={"name": "Cabinet Intégration", "email": f"integ-{uuid.uuid4().hex[:8]}@test.fr"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestParcoursComplet:
    def test_01_cabinet_a_un_trial(self, client, cabinet_id):
        r = client.get(f"/billing/status", params={"cabinet_id": cabinet_id})
        assert r.status_code == 200
        body = r.json()
        assert body["trial_active"] is True
        assert body["has_access"] is True

    def test_02_upload_et_ocr(self, client, cabinet_id):
        files = {"file": ("facture.pdf", PDF_BYTES, "application/pdf")}
        r = client.post("/invoices/upload", files=files, data={"cabinet_id": cabinet_id})
        assert r.status_code == 202, r.text
        invoice_id = r.json()["id"]

        # Attendre la fin du job OCR (worker async)
        for _ in range(20):
            inv = client.get(f"/invoices/{invoice_id}").json()
            if inv["status"] not in ("pending", "processing"):
                break
            time.sleep(1)
        assert inv["status"] in ("needs_review", "validated")

        # Mémoriser pour les tests suivants
        type(self).invoice_id = invoice_id

    def test_03_upload_doublon_rejete(self, client, cabinet_id):
        files = {"file": ("facture_copie.pdf", PDF_BYTES, "application/pdf")}
        r = client.post("/invoices/upload", files=files, data={"cabinet_id": cabinet_id})
        assert r.status_code == 409
        assert "doublon" in r.json()["detail"].lower()

    def test_04_format_non_supporte_rejete(self, client, cabinet_id):
        files = {"file": ("script.exe", b"MZ...", "application/x-msdownload")}
        r = client.post("/invoices/upload", files=files, data={"cabinet_id": cabinet_id})
        assert r.status_code == 415

    def test_05_correction_humaine(self, client):
        r = client.patch(
            f"/invoices/{self.invoice_id}",
            json={"vendor_name": "EDF", "amount_ttc": 120.0, "pcg_account": "606100"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "validated"
        assert r.json()["pcg_source"] == "manual"

    def test_06_export_ebp(self, client):
        r = client.post(f"/invoices/{self.invoice_id}/export", params={"format": "ebp"})
        assert r.status_code == 200
        text = r.content.decode("utf-8-sig")
        assert text.startswith("Date;Compte;")
        assert "606100" in text

    def test_07_export_sage(self, client):
        r = client.post(f"/invoices/{self.invoice_id}/export", params={"format": "sage50"})
        assert r.status_code == 200
        assert r.content.decode("latin-1").startswith("Date,Compte,")

    def test_08_fichier_servi_pour_apercu(self, client):
        r = client.get(f"/invoices/{self.invoice_id}/file")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")

    def test_09_reprocess(self, client):
        r = client.post(f"/invoices/{self.invoice_id}/reprocess")
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_10_facture_inexistante_404(self, client):
        r = client.get(f"/invoices/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_11_checkout_sans_stripe_503(self, client, cabinet_id):
        r = client.post("/billing/checkout-session", json={"cabinet_id": cabinet_id})
        # Sans clé Stripe configurée → 503 explicite (pas un crash)
        assert r.status_code == 503
