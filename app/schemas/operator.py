from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class OperatorCreate(BaseModel):
    """Dados para criar um novo operador."""
    name: str
    email: EmailStr
    password: str


class OperatorResponse(BaseModel):
    """Dados públicos de um operador retornados pela API."""
    model_config = {"from_attributes": True}

    id: str
    name: Optional[str]
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]