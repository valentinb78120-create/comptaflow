"""
Dépendances FastAPI partagées — résolution du cabinet courant.

Deux modes coexistent en V1 :
- **Authentifié** : header `Authorization: Bearer <jwt>` → cabinet du token
- **Démo** : pas de token, le client fournit explicitement `cabinet_id`
  (cabinets créés sans mot de passe via POST /cabinets/)

Quand un token est présent ET qu'un cabinet_id explicite est fourni,
ils doivent correspondre (403 sinon) — un cabinet ne lit pas les données
d'un autre.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import InvalidTokenError, decode_access_token
from app.models.cabinet import Cabinet


async def get_token_cabinet_id(
    authorization: str | None = Header(None),
) -> uuid.UUID | None:
    """Extrait l'id cabinet du Bearer token, ou None si pas de token."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="En-tête Authorization invalide (attendu: Bearer <token>)",
        )
    try:
        return decode_access_token(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou invalide — reconnectez-vous",
        )


def resolve_cabinet_id(
    explicit_id: uuid.UUID | None,
    token_id: uuid.UUID | None,
) -> uuid.UUID:
    """
    Combine token et paramètre explicite en un cabinet_id effectif.
    - token seul → token
    - explicite seul → explicite (mode démo)
    - les deux → doivent correspondre
    - aucun → 401
    """
    if token_id is not None:
        if explicit_id is not None and explicit_id != token_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce cabinet ne vous appartient pas",
            )
        return token_id
    if explicit_id is not None:
        return explicit_id
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise (token ou cabinet_id)",
    )


async def get_current_cabinet(
    token_id: uuid.UUID | None = Depends(get_token_cabinet_id),
    db: AsyncSession = Depends(get_db),
) -> Cabinet:
    """Cabinet authentifié obligatoire (401 sans token valide)."""
    if token_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
        )
    cabinet = await db.get(Cabinet, token_id)
    if cabinet is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte introuvable",
        )
    return cabinet


async def get_current_admin(
    cabinet: Cabinet = Depends(get_current_cabinet),
) -> Cabinet:
    """Cabinet authentifié AVEC rôle admin (403 sinon)."""
    if not cabinet.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return cabinet
