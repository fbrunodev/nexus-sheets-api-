from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime
from app.models.sheet import SheetStatus, CooperationType
from app.services.calculations import calc_line_result, calc_sheet_result

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
    created_at: datetime

    @computed_field
    @property
    def result(self) -> float:
        
        return calc_line_result(self)

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
    cooperation_type: Optional[str] = "META"


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
    cooperation_type: CooperationType = CooperationType.META

    @computed_field
    @property
    def result(self) -> float:
        return calc_sheet_result(self)
