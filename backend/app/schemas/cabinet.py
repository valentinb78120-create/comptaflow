"""Pydantic schemas for Cabinet."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CabinetCreate(BaseModel):
    name: str
    email: EmailStr
    siret: str | None = None


class CabinetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    siret: str | None
    subscription_active: bool
    trial_ends_at: datetime | None
    is_admin: bool = False
    plan: str = "cabinet"
    created_at: datetime
