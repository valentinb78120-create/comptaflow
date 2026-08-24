"""Tests d'intégration du back-office admin."""
import uuid

import httpx
import pytest

BASE = "http://localhost:8000/api/v1"


def stack_up() -> bool:
    try:
        return httpx.get("http://localhost:8000/health", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not stack_up(), reason="API non démarrée")


def promote_to_admin(email: str) -> None:
    """Promotion directe en DB (le test tourne dans le container api)."""
    from sqlalchemy import create_engine, text
    from app.core.config import get_settings

    engine = create_engine(get_settings().database_url_sync)
    with engine.begin() as conn:
        conn.execute(text("UPDATE cabinets SET is_admin = true WHERE email = :e"), {"e": email})
    engine.dispose()


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        yield c


@pytest.fixture(scope="module")
def admin_headers(client) -> dict:
    email = f"admin-test-{uuid.uuid4().hex[:8]}@test.fr"
    r = client.post("/auth/register", json={"name": "Admin Test", "email": email, "password": "AdminPass123"})
    assert r.status_code == 201
    promote_to_admin(email)
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def user_headers(client) -> dict:
    email = f"user-test-{uuid.uuid4().hex[:8]}@test.fr"
    r = client.post("/auth/register", json={"name": "User Lambda", "email": email, "password": "UserPass123"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


class TestAdminAccess:
    def test_sans_token_401(self, client):
        assert client.get("/admin/stats").status_code == 401

    def test_user_normal_403(self, client, user_headers):
        assert client.get("/admin/stats", headers=user_headers).status_code == 403

    def test_admin_voit_les_stats(self, client, admin_headers):
        r = client.get("/admin/stats", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["cabinets_total"] >= 2
        assert "needs_review" in body["invoices_by_status"]

    def test_admin_liste_les_cabinets(self, client, admin_headers):
        r = client.get("/admin/cabinets", headers=admin_headers)
        assert r.status_code == 200
        assert any("invoice_count" in row for row in r.json())


class TestAdminActions:
    def test_extend_trial(self, client, admin_headers):
        cible = client.post(
            "/cabinets/",
            json={"name": "Cible Trial", "email": f"cible-{uuid.uuid4().hex[:8]}@test.fr"},
        ).json()
        avant = cible["trial_ends_at"]
        r = client.post(f"/admin/cabinets/{cible['id']}/extend-trial", params={"days": 30}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["trial_ends_at"] > avant

    def test_toggle_subscription(self, client, admin_headers):
        cible = client.post(
            "/cabinets/",
            json={"name": "Cible Abo", "email": f"abo-{uuid.uuid4().hex[:8]}@test.fr"},
        ).json()
        r1 = client.post(f"/admin/cabinets/{cible['id']}/toggle-subscription", headers=admin_headers)
        assert r1.json()["subscription_active"] is True
        r2 = client.post(f"/admin/cabinets/{cible['id']}/toggle-subscription", headers=admin_headers)
        assert r2.json()["subscription_active"] is False

    def test_cabinet_inexistant_404(self, client, admin_headers):
        r = client.post(f"/admin/cabinets/{uuid.uuid4()}/extend-trial", headers=admin_headers)
        assert r.status_code == 404


class TestSiretAtRegister:
    def test_siret_invalide_rejete(self, client):
        r = client.post(
            "/auth/register",
            json={
                "name": "Cabinet SIRET KO",
                "email": f"siret-{uuid.uuid4().hex[:8]}@test.fr",
                "password": "Password123",
                "siret": "12345678901234",
            },
        )
        assert r.status_code == 422
        assert "SIRET" in r.text

    def test_siret_valide_accepte(self, client):
        r = client.post(
            "/auth/register",
            json={
                "name": "Cabinet SIRET OK",
                "email": f"siret-{uuid.uuid4().hex[:8]}@test.fr",
                "password": "Password123",
                "siret": "73282932000074",
            },
        )
        assert r.status_code == 201
        assert r.json()["cabinet"]["siret"] == "73282932000074"
