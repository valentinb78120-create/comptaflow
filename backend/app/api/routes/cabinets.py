"""Cabinet management routes."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.cabinet import Cabinet
from app.schemas.cabinet import CabinetCreate, CabinetOut

router = APIRouter(prefix="/cabinets", tags=["cabinets"])

TRIAL_DAYS = 14


@router.post("/", response_model=CabinetOut, status_code=status.HTTP_201_CREATED)
async def create_cabinet(payload: CabinetCreate, db: AsyncSession = Depends(get_db)) -> Cabinet:
    """Create a new cabinet account with a 14-day free trial."""
    existing = await db.execute(select(Cabinet).where(Cabinet.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    cabinet = Cabinet(
        **payload.model_dump(),
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS),
    )
    db.add(cabinet)
    await db.commit()
    await db.refresh(cabinet)
    return cabinet


@router.get("/{cabinet_id}", response_model=CabinetOut)
async def get_cabinet(cabinet_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Cabinet:
    """Return cabinet details."""
    cabinet = await db.get(Cabinet, cabinet_id)
    if cabinet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable")
    return cabinet
