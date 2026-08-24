"""
Sécurité : hachage de mot de passe (bcrypt) et tokens JWT.

Le JWT contient l'id du cabinet (`sub`) et expire après 7 jours.
Secret = APP_SECRET_KEY (à changer en production).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(days=7)


class InvalidTokenError(Exception):
    """Token absent, expiré ou falsifié."""


def hash_password(password: str) -> str:
    """Hache un mot de passe avec bcrypt (salt automatique)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Compare un mot de passe en clair au hash stocké."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(cabinet_id: uuid.UUID) -> str:
    """Crée un JWT signé portant l'id du cabinet."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(cabinet_id),
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    """
    Vérifie et décode un JWT.
    Retourne l'id du cabinet ; lève InvalidTokenError sinon.
    """
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise InvalidTokenError(str(exc)) from exc
