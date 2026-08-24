"""Tests d'intégration des features V1.5 : change-password, règles custom, export FEC."""
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
    email = f"v15-{uuid.uuid4().hex[:8]}@test.fr"
    r = client.post("/auth/register", json={"name": "Cabinet V15", "email": email, "password": "AncienMdp123"})
    body = r.json()
    return {"email": email, "headers": {"Authorization": f"Bearer {body['token']}"}, "cabinet_id": body["cabinet"]["id"]}


class TestChangePassword:
    def test_mauvais_mdp_actuel_401(self, client, account):
        r = client.post(
            "/auth/change-password",
            json={"current_password": "faux", "new_password": "NouveauMdp123"},
            headers=account["headers"],
        )
        assert r.status_code == 401

    def test_changement_puis_login(self, client, account):
        r = client.post(
            "/auth/change-password",
            json={"current_password": "AncienMdp123", "new_password": "NouveauMdp456"},
            headers=account["headers"],
        )
        assert r.status_code == 204

        # Ancien mot de passe refusé, nouveau accepté
        assert client.post("/auth/login", json={"email": account["email"], "password": "AncienMdp123"}).status_code == 401
        assert client.post("/auth/login", json={"email": account["email"], "password": "NouveauMdp456"}).status_code == 200

    def test_sans_token_401(self, client):
        r = client.post("/auth/change-password", json={"current_password": "x", "new_password": "ValidePass1"})
        assert r.status_code == 401


class TestCustomRules:
    def test_crud_complet(self, client, account):
        h = account["headers"]
        # Création
        r = client.post(
            "/pcg-rules/custom",
            json={"keywords": ["boulangerie dupont"], "account": "606300", "label": "Frais de réception"},
            headers=h,
        )
        assert r.status_code == 201, r.text
        rule_id = r.json()["id"]

        # Listing
        rules = client.get("/pcg-rules/custom", headers=h).json()
        assert any(r["id"] == rule_id for r in rules)

        # Suppression
        assert client.delete(f"/pcg-rules/custom/{rule_id}", headers=h).status_code == 204
        assert client.get("/pcg-rules/custom", headers=h).json() == []

    def test_compte_invalide_422(self, client, account):
        r = client.post(
            "/pcg-rules/custom",
            json={"keywords": ["x"], "account": "abc", "label": "Test"},
            headers=account["headers"],
        )
        assert r.status_code == 422

    def test_isolation_entre_cabinets(self, client, account):
        """Un cabinet ne peut pas supprimer la règle d'un autre."""
        h = account["headers"]
        rule = client.post(
            "/pcg-rules/custom",
            json={"keywords": ["secret"], "account": "606100", "label": "Privée"},
            headers=h,
        ).json()

        autre = client.post(
            "/auth/register",
            json={"name": "Autre", "email": f"autre-{uuid.uuid4().hex[:8]}@test.fr", "password": "Password123"},
        ).json()
        h2 = {"Authorization": f"Bearer {autre['token']}"}

        assert client.get("/pcg-rules/custom", headers=h2).json() == []
        assert client.delete(f"/pcg-rules/custom/{rule['id']}", headers=h2).status_code == 404

        client.delete(f"/pcg-rules/custom/{rule['id']}", headers=h)  # nettoyage


class TestToggleStandardRule:
    def test_toggle_aller_retour(self, client, account):
        h = account["headers"]
        # Récupère une clé de règle standard
        rules = client.get("/pcg-rules/").json()
        key = rules[0]["key"]

        # Désactivation
        r1 = client.post("/pcg-rules/standard/toggle", json={"key": key}, headers=h)
        assert r1.status_code == 200
        assert r1.json()["disabled"] is True
        assert key in client.get("/pcg-rules/disabled", headers=h).json()

        # Réactivation
        r2 = client.post("/pcg-rules/standard/toggle", json={"key": key}, headers=h)
        assert r2.json()["disabled"] is False
        assert key not in client.get("/pcg-rules/disabled", headers=h).json()

    def test_cle_inconnue_400(self, client, account):
        r = client.post("/pcg-rules/standard/toggle", json={"key": "000000:Bidon"}, headers=account["headers"])
        assert r.status_code == 400

    def test_sans_token_401(self, client):
        assert client.post("/pcg-rules/standard/toggle", json={"key": "x"}).status_code == 401

    def test_isolation_par_cabinet(self, client, account):
        """La désactivation d'un cabinet n'affecte pas les autres."""
        h = account["headers"]
        rules = client.get("/pcg-rules/").json()
        key = rules[1]["key"]
        client.post("/pcg-rules/standard/toggle", json={"key": key}, headers=h)

        autre = client.post(
            "/auth/register",
            json={"name": "Isolé", "email": f"iso-{uuid.uuid4().hex[:8]}@test.fr", "password": "Password123"},
        ).json()
        h2 = {"Authorization": f"Bearer {autre['token']}"}
        assert client.get("/pcg-rules/disabled", headers=h2).json() == []

        client.post("/pcg-rules/standard/toggle", json={"key": key}, headers=h)  # nettoyage


class TestPlansEtQuota:
    def test_status_expose_plan_et_usage(self, client, account):
        r = client.get("/billing/status", params={"cabinet_id": account["cabinet_id"]})
        assert r.status_code == 200
        body = r.json()
        assert body["plan"] == "cabinet"
        assert body["plan_label"] == "Cabinet"
        assert body["monthly_limit"] == 1000
        assert isinstance(body["monthly_used"], int)

    def test_quota_decouverte_bloque_a_100(self, client, account):
        """Passe le cabinet en Découverte avec 100 factures simulées → upload refusé 402."""
        from sqlalchemy import create_engine, text
        from app.core.config import get_settings

        engine = create_engine(get_settings().database_url_sync)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE cabinets SET plan = 'decouverte' WHERE id = :i"),
                {"i": account["cabinet_id"]},
            )
            # Simule 100 factures ce mois-ci (lignes minimales)
            for n in range(100):
                conn.execute(
                    text(
                        "INSERT INTO invoices (id, cabinet_id, original_filename, storage_path, "
                        "file_mime_type, status, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :c, 'q.pdf', '/tmp/q', 'application/pdf', "
                        "'validated', now(), now())"
                    ),
                    {"c": account["cabinet_id"]},
                )
        engine.dispose()

        pdf = b"%PDF-1.4 quota-test " + uuid.uuid4().hex.encode()
        r = client.post(
            "/invoices/upload",
            files={"file": ("quota.pdf", pdf, "application/pdf")},
            headers=account["headers"],
        )
        assert r.status_code == 402
        assert "Quota mensuel atteint" in r.json()["detail"]

        # Retour au plan cabinet → l'upload repasse
        with create_engine(get_settings().database_url_sync).begin() as conn:
            conn.execute(
                text("UPDATE cabinets SET plan = 'cabinet' WHERE id = :i"),
                {"i": account["cabinet_id"]},
            )
        r2 = client.post(
            "/invoices/upload",
            files={"file": ("quota2.pdf", pdf + b"2", "application/pdf")},
            headers=account["headers"],
        )
        assert r2.status_code == 202


class TestFecEndpoint:
    def test_export_fec_bulk(self, client, account):
        h = account["headers"]
        # Une facture validée minimale via upload + patch
        pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF" + uuid.uuid4().hex.encode()
        up = client.post("/invoices/upload", files={"file": ("f.pdf", pdf, "application/pdf")}, headers=h)
        assert up.status_code == 202
        inv_id = up.json()["id"]
        client.patch(f"/invoices/{inv_id}", json={"vendor_name": "EDF", "amount_ht": 100, "amount_tva": 20, "amount_ttc": 120}, headers=h)

        r = client.post("/invoices/export/bulk", params={"format": "fec"}, headers=h)
        assert r.status_code == 200
        assert "FEC" in r.headers["content-disposition"]
        body = r.content.decode("iso-8859-15")
        assert body.startswith("JournalCode\tJournalLib")
        assert "401000" in body
