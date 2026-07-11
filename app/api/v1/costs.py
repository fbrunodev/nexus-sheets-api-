from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.cost import CostTypeCreate, CostTypeResponse, CostCreate, CostResponse
from app.models.cost import CostType
from app.services.cost import (
    list_cost_types,
    create_cost_type,
    list_costs,
    create_cost,
    delete_cost,
)
from fastapi import HTTPException, status

router = APIRouter(prefix="/costs", tags=["Costs"])


def require_admin(current_user: User) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Requer role ADMIN."
        )
    return current_user


@router.get("/types", response_model=list[CostTypeResponse])
def get_cost_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_cost_types(db)


@router.post("/types", response_model=CostTypeResponse, status_code=201)
def create_cost_type_endpoint(
    data: CostTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return create_cost_type(db, data, current_user.id)


@router.get("/", response_model=list[CostResponse])
def get_costs(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_costs(db, current_user.id, month, year)


@router.post("/", response_model=CostResponse, status_code=201)
def create_cost_endpoint(
    data: CostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_cost(db, data, current_user.id)


@router.delete("/types/{cost_type_id}", status_code=204)
def delete_cost_type_endpoint(
    cost_type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    cost_type = db.query(CostType).filter(CostType.id == cost_type_id).first()
    if not cost_type:
        raise HTTPException(status_code=404, detail="Tipo de custo não encontrado.")
    db.delete(cost_type)
    db.commit()


@router.delete("/{cost_id}", status_code=204)
def delete_cost_endpoint(
    cost_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_cost(db, cost_id, current_user.id)


@router.get("/stats")
def get_cost_stats(
    period: str = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.cost import Cost
    from sqlalchemy import func
    from datetime import datetime

    now = datetime.utcnow()
    query = db.query(
        CostType.name,
        func.sum(Cost.value).label("total")
    ).join(Cost, Cost.cost_type_id == CostType.id).filter(
        Cost.owner_id == current_user.id
    )

    if period in ("today", "month"):
        query = query.filter(Cost.year == now.year, Cost.month == now.month)
    elif period == "week":
        query = query.filter(Cost.year == now.year, Cost.month == now.month)

    results = query.group_by(CostType.name).all()

    return [{"name": r.name, "value": float(r.total)} for r in results]
