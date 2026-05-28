from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import get_dashboard_data

# Agrupa todos os endpoints do dashboard
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=DashboardResponse)
def dashboard(
    period: str = Query(
        default="all",
        description="Período de filtro: all, month, week, today"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna todas as métricas agregadas do dashboard.
    Filtra por período via query parameter.
    
    Exemplos:
    - /dashboard/?period=all
    - /dashboard/?period=month
    - /dashboard/?period=week
    - /dashboard/?period=today
    """
    return get_dashboard_data(db, current_user.id, period)