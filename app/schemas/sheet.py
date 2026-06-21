from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.sheet import SheetStatus


# --------------SHEET LINE SCHEMAS-------------------------------

class SheetLineCreate(BaseModel):
    """Dados para criar uma nova linha na planilha"""
    line_number: int
    deposit: float = 0
    withdrawal: float = 0
    chest: float = 0


class SheetLineUpdate(BaseModel):
    """Dados para atualizar uma linha existente"""
    deposit: Optional[float] = None
    withdrawal: Optional[float] = None
    chest: Optional[float] = None
    bonus: Optional[float] = None


class SheetLineResponse(BaseModel):
    """Dados de uma linha retornados pela API."""
    model_config = {"from_attributes": True}

    id: str
    sheet_id: str
    line_number: int
    deposit: float
    withdrawal: float
    chest: float
    bonus: float
    result: float
    created_at: datetime


# ----------------- SHEET SCHEMAS-------------------------------------

class SheetCreate(BaseModel):
    """Dados para criar uma nova planilha"""
    name: str
    operator_id: Optional[str]= None
    # Número de linhas iniciais - padrão 1
    initial_lines: int = 1
    goal: int = 0
    deposits: Optional[list[float]] = None
    platform_id: Optional[str] = None


class SheetUpdate(BaseModel):
    """Dados para atualizar uma planilha existente."""
    name: Optional[str] = None
    operator_id: Optional[str] = None
    salary: Optional[float] = None
    goal: Optional[int] = None



class SheetResponse(BaseModel):
    """Dados completos de uma planilha retornados pela API."""
    model_config = {"from_attributes": True}


    id: str
    name: str
    owner_id: str
    operator_id: Optional[str]
    status: SheetStatus
    salary: float
    created_at: datetime
    updated_at: datetime
    lines: List[SheetLineResponse] = []
    goal: int
    platform_id: Optional[str] = None
    