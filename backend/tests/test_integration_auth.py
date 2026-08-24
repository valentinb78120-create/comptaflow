"""Tests d'intégration du flux d'authentification complet."""
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


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        yield c


@pytest.fixture(scope="module")
def account(client) -> dict:
    """Compte inscrit une fois pour tout le module."""
    email = f"auth-integ-{uuid.uuid4().hex[:8]}@test.fr"
    r = client.post(
        "/auth/register",
        json={"name": "Cabinet Auth", "email": email, "password": "SuperSecret99"},
    )
    assert r.status_code == 201, r.text
    return {**r.json(), "email": email, "password": "SuperSecret99"}


class TestAuthFlow:
    def test_register_donne_token_et_trial(self, client, account):
        assert account["token"]
        assert account["cabinet"]["trial_ends_at"] is not None

    def test_email_duplique_409(self, client, account):
        r = client.post(
            "/auth/register",
            json={"name": "Doublon", "email": account["email"], "password": "Autre1234"},
        )
        assert r.status_code == 409

    def test_login_ok(self, client, account):
        r = client.post("/auth/login", json={"email": account["email"], "password": account["password"]})
        assert r.status_code == 200
        assert r.json()["token"]

    def test_login_mauvais_mdp_401(self, client, account):
        r = client.post("/auth/login", json={"email": account["email"], "password": "faux-mdp-123"})
        assert r.status_code == 401

    def test_me_avec_token(self, client, account):
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {account['token']}"})
        assert r.status_code == 200
        assert r.json()["email"] == account["email"]

    def test_me_sans_token_401(self, client):
        assert client.get("/auth/me").status_code == 401

    def test_liste_factures_via_token_seul(self, client, account):
        """Le token suffit — plus besoin de passer cabinet_id."""
        r = client.get("/invoices/", headers={"Authorization": f"Bearer {account['token']}"})
        assert r.status_code == 200
        assert r.json() == []  # nouveau cabinet, aucune facture

    def test_liste_sans_token_ni_cabinet_id_401(self, client):
        assert client.get("/invoices/").status_code == 401

    def test_cabinet_d_autrui_interdit_403(self, client, account):
        """Token du cabinet A + cabinet_id de B → refus."""
        autre = client.post(
            "/cabinets/",
            json={"name": "Autre Cabinet", "email": f"autre-{uuid.uuid4().hex[:8]}@test.fr"},
        ).json()
        r = client.get(
            "/invoices/",
            params={"cabinet_id": autre["id"]},
            headers={"Authorization": f"Bearer {account['token']}"},
        )
        assert r.status_code == 403

    def test_mode_demo_sans_token_fonctionne(self, client):
        """Compat V1 : cabinet_id explicite sans token reste accepté."""
        demo = client.post(
            "/cabinets/",
            json={"name": "Démo", "email": f"demo-{uuid.uuid4().hex[:8]}@test.fr"},
        ).json()
        r = client.get("/invoices/", params={"cabinet_id": demo["id"]})
        assert r.status_code == 200
