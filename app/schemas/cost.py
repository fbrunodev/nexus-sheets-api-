from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CostTypeCreate(BaseModel):
    name: str


class CostTypeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    created_at: datetime


class CostCreate(BaseModel):
    cost_type_id: str
    value: float
    month: int
    year: int
    description: Optional[str] = None


class CostResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    cost_type_id: str
    cost_type: CostTypeResponse
    owner_id: str
    value: float
    month: int
    year: int
    description: Optional[str]
    created_at: datetime
