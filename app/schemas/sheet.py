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


class SheetLineResponse(BaseModel):
    """Dados de uma linha retornados pela API."""
    model_config = {"from_attributes": True}

    id: str
    sheet_id: str
    line_number: int
    deposit: float
    withdrawal: float
    chest: float
    # Resultado calculado automaticamente: saque + baú - deposito

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
    
class SheetUpdate(BaseModel):
    """Dados para atualizar uma planilha existente."""
    name: Optional[str] = None
    operator_id: Optional[str] = None
    cost_proxy: Optional[float] = None
    cost_sms: Optional[float] = None
    cost_bot: Optional[float] = None
    cost_fintech: Optional[float] = None
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
    cost_proxy: float
    cost_sms: float
    cost_bot: float
    cost_fintech: float
    salary: float
    created_at: datetime
    updated_at: datetime
    lines: List[SheetLineResponse] = []
    goal: int
    #Campos calculados dinamicamente

    @property
    def total_deposited(self) -> float:
        """Total depositado em todas as linhas"""
        return sum(line.withdrawal for line in self.lines)
    

    @property
    def total_received(self) -> float:
        """Total recebido (saques) em todas as linhas."""
        return sum(line.withdrawal for line in self.lines)
    

    @property
    def total_chest(self) -> float:
        """Total em baús em todas as linhas"""
        return sum(line.chest for line in self.lines)
    

    @property
    def total_costs(self) -> float:
        """Soma de todos os custos operacionais"""
        return self.cost_proxy + self.cost_sms + self.cost_bot + self.cost_fintech
    
    @property
    def final_result(self) -> float:
        """Resultado final: recebido + baú - depositado- custos"""
        return (self.total_received - abs(self.total_deposited) ) + self.salary + self.total_chest
    