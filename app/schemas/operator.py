from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class OperatorCreate(BaseModel):
    """Dados para criar um novo operador."""
    email: EmailStr
    password: str
    name: Optional[str] = None


class OperatorResponse(BaseModel):
    """Dados públicos de um operador retornados pela API."""
    model_config = {"from_attributes": True}

    id: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]