from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.user import PlanType


class ActivationKeyCreate(BaseModel):
    """Dados para gerar uma nova activation key."""
    type: PlanType
    # Expiração opcional — apenas para keys MONTHLY e TRIAL
    expires_at: Optional[datetime] = None


class ActivationKeyResponse(BaseModel):
    """Dados de uma activation key retornados pela API."""
    model_config = {"from_attributes": True}

    id: str
    key: str
    type: PlanType
    expires_at: Optional[datetime]
    is_used: bool
    used_by: Optional[str]
    created_at: datetime