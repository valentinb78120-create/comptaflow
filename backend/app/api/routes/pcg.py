"""
Règles de catégorisation PCG.

GET    /pcg-rules/            — règles standard (lecture seule)
GET    /pcg-rules/custom      — règles personnalisées du cabinet connecté
POST   /pcg-rules/custom      — ajouter une règle (prioritaire sur le standard)
DELETE /pcg-rules/custom/{id} — supprimer une de ses règles
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_cabinet
from app.core.database import get_db
from app.models.cabinet import Cabinet
from app.models.pcg_rule import PCGCustomRule
from app.services.pcg_categorizer import get_all_rules, is_valid_rule_key

router = APIRouter(prefix="/pcg-rules", tags=["pcg"])

MAX_RULES_PER_CABINET = 200


class PCGRuleOut(BaseModel):
    key: str
    keywords: list[str]
    account: str
    label: str


class ToggleRuleIn(BaseModel):
    key: str


class ToggleRuleOut(BaseModel):
    key: str
    disabled: bool


class CustomRuleIn(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=20)
    account: str
    label: str = Field(min_length=2, max_length=255)

    @field_validator("account")
    @classmethod
    def account_pcg(cls, v: str) -> str:
        if not (v.isdigit() and 6 <= len(v) <= 8):
            raise ValueError("Compte PCG : 6 à 8 chiffres (ex : 606100)")
        return v

    @field_validator("keywords")
    @classmethod
    def keywords_clean(cls, v: list[str]) -> list[str]:
        cleaned = [k.strip() for k in v if k.strip()]
        if not cleaned:
            raise ValueError("Au moins un mot-clé non vide")
        if any(len(k) > 64 for k in cleaned):
            raise ValueError("Mot-clé trop long (max 64 caractères)")
        return cleaned


class CustomRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    keywords: list[str]
    account: str
    label: str


@router.get("/", response_model=list[PCGRuleOut])
async def list_pcg_rules() -> list[dict]:
    """Liste des règles de catégorisation standard (communes à tous)."""
    return get_all_rules()


@router.get("/disabled", response_model=list[str])
async def list_disabled_rules(
    cabinet: Cabinet = Depends(get_current_cabinet),
) -> list[str]:
    """Clés des règles standard désactivées par le cabinet connecté."""
    return list(cabinet.disabled_pcg_rules or [])


@router.post("/standard/toggle", response_model=ToggleRuleOut)
async def toggle_standard_rule(
    payload: ToggleRuleIn,
    cabinet: Cabinet = Depends(get_current_cabinet),
    db: AsyncSession = Depends(get_db),
) -> ToggleRuleOut:
    """
    Active/désactive une règle standard pour CE cabinet uniquement.
    Une règle désactivée n'est plus appliquée par l'OCR de ce cabinet.
    """
    if not is_valid_rule_key(payload.key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Règle standard inconnue",
        )

    disabled = set(cabinet.disabled_pcg_rules or [])
    if payload.key in disabled:
        disabled.discard(payload.key)
        now_disabled = False
    else:
        disabled.add(payload.key)
        now_disabled = True

    # Réaffectation obligatoire : SQLAlchemy ne détecte pas les mutations en place sur JSON
    cabinet.disabled_pcg_rules = sorted(disabled)
    await db.commit()
    return ToggleRuleOut(key=payload.key, disabled=now_disabled)


@router.get("/custom", response_model=list[CustomRuleOut])
async def list_custom_rules(
    cabinet: Cabinet = Depends(get_current_cabinet),
    db: AsyncSession = Depends(get_db),
) -> list[PCGCustomRule]:
    """Règles personnalisées du cabinet connecté (prioritaires sur le standard)."""
    rows = await db.execute(
        select(PCGCustomRule)
        .where(PCGCustomRule.cabinet_id == cabinet.id)
        .order_by(PCGCustomRule.created_at.desc())
    )
    return list(rows.scalars().all())


@router.post("/custom", response_model=CustomRuleOut, status_code=status.HTTP_201_CREATED)
async def create_custom_rule(
    payload: CustomRuleIn,
    cabinet: Cabinet = Depends(get_current_cabinet),
    db: AsyncSession = Depends(get_db),
) -> PCGCustomRule:
    """Ajoute une règle personnalisée au cabinet connecté."""
    count = len(
        (await db.execute(
            select(PCGCustomRule.id).where(PCGCustomRule.cabinet_id == cabinet.id)
        )).scalars().all()
    )
    if count >= MAX_RULES_PER_CABINET:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Limite de {MAX_RULES_PER_CABINET} règles atteinte",
        )

    rule = PCGCustomRule(
        cabinet_id=cabinet.id,
        keywords=payload.keywords,
        account=payload.account,
        label=payload.label,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/custom/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_rule(
    rule_id: uuid.UUID,
    cabinet: Cabinet = Depends(get_current_cabinet),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Supprime une règle personnalisée (uniquement les siennes)."""
    rule = await db.get(PCGCustomRule, rule_id)
    if rule is None or rule.cabinet_id != cabinet.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle introuvable")
    await db.delete(rule)
    await db.commit()
