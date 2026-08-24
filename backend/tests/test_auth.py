"""Tests unitaires de la sécurité (bcrypt + JWT)."""
import uuid

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswords:
    def test_hash_et_verify(self):
        h = hash_password("MonMotDePasse123!")
        assert h != "MonMotDePasse123!"
        assert verify_password("MonMotDePasse123!", h) is True

    def test_mauvais_mot_de_passe(self):
        h = hash_password("correct")
        assert verify_password("incorrect", h) is False

    def test_hash_unique_par_salt(self):
        assert hash_password("abc12345") != hash_password("abc12345")

    def test_hash_corrompu_ne_crashe_pas(self):
        assert verify_password("x", "pas-un-hash-bcrypt") is False


class TestTokens:
    def test_roundtrip(self):
        cabinet_id = uuid.uuid4()
        token = create_access_token(cabinet_id)
        assert decode_access_token(token) == cabinet_id

    def test_token_falsifie_rejete(self):
        token = create_access_token(uuid.uuid4())
        falsifie = token[:-4] + "XXXX"
        with pytest.raises(InvalidTokenError):
            decode_access_token(falsifie)

    def test_token_vide_rejete(self):
        with pytest.raises(InvalidTokenError):
            decode_access_token("")

    def test_token_autre_secret_rejete(self):
        import jwt as pyjwt
        forge = pyjwt.encode({"sub": str(uuid.uuid4())}, "mauvais-secret", algorithm="HS256")
        with pytest.raises(InvalidTokenError):
            decode_access_token(forge)
