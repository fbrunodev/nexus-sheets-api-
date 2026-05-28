from pydantic import BaseModel
from typing import List
from datetime import datetime


class CostSummary(BaseModel):
    """
    Resumo dos custos operacionais
    """

    proxy: float
    sms: float
    bot: float
    fintech: float
    total: float


class MonthlyPerformance(BaseModel):
    """Dados de perfomance de um mês específico."""
    month: str  # ex: "2026-01"
    deposited: float
    received: float
    result: float

class DashboardResponse(BaseModel):
    """
    Resposta completa do dashboard.
    Todos os dados são calculados dinamicamente
    com base nas planilhas do usuário autenticado.
    """

    # Resumo financeiro
    total_deposited: float
    total_received: float
    total_chest: float
    final_result: float


    # Custos
    costs : CostSummary

    # Contadores
    total_sheets: int
    total_operations: int # total linhas preenchidas

    # Gráficos
    monthly_performance: List[MonthlyPerformance]