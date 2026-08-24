"""
Authentification — inscription, connexion, profil.

POST /auth/register — crée un cabinet avec mot de passe + trial 14j → token
POST /auth/login    — email + mot de passe → token
GET  /auth/me       — profil du cabinet connecté (Bearer)
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.siret import validate_siret
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_cabinet
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.cabinet import Cabinet
from app.schemas.cabinet import CabinetOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

TRIAL_DAYS = 14


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    siret: str | None = Field(None, max_length=20)

    @field_validator("siret")
    @classmethod
    def siret_must_be_valid(cls, v: str | None) -> str | None:
        """SIRET optionnel mais, si fourni, structurellement valide (Luhn)."""
        if v is None or v.strip() == "":
            return None
        if not validate_siret(v):
            raise ValueError("SIRET invalide (14 chiffres, contrôle de Luhn)")
        return v.replace(" ", "")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    cabinet: CabinetOut


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Inscription d'un cabinet : compte + mot de passe + trial 14 jours."""
    existing = await db.execute(select(Cabinet).where(Cabinet.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    cabinet = Cabinet(
        name=payload.name,
        email=payload.email,
        siret=payload.siret,
        password_hash=hash_password(payload.password),
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS),
    )
    db.add(cabinet)
    await db.commit()
    await db.refresh(cabinet)

    logger.info("Nouveau cabinet inscrit: %s", cabinet.id)
    return AuthResponse(token=create_access_token(cabinet.id), cabinet=CabinetOut.model_validate(cabinet))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Connexion par email + mot de passe."""
    result = await db.execute(select(Cabinet).where(Cabinet.email == payload.email))
    cabinet = result.scalar_one_or_none()

    # Message identique que l'email existe ou non (pas d'énumération de comptes)
    if cabinet is None or not cabinet.password_hash or not verify_password(payload.password, cabinet.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    return AuthResponse(token=create_access_token(cabinet.id), cabinet=CabinetOut.model_validate(cabinet))


@router.get("/me", response_model=CabinetOut)
async def me(cabinet: Cabinet = Depends(get_current_cabinet)) -> Cabinet:
    """Profil du cabinet connecté."""
    return cabinet


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    cabinet: Cabinet = Depends(get_current_cabinet),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change le mot de passe du compte connecté (mot de passe actuel requis)."""
    if not cabinet.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte démo sans mot de passe — créez un compte",
        )
    if not verify_password(payload.current_password, cabinet.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe actuel incorrect",
        )

    cabinet.password_hash = hash_password(payload.new_password)
    await db.commit()
    logger.info("Mot de passe changé pour le cabinet %s", cabinet.id)
