from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.cost import CostTypeCreate, CostTypeResponse, CostCreate, CostResponse
from app.services.cost import (
    list_cost_types,
    create_cost_type,
    delete_cost_type,
    list_costs,
    add_cost_to_a_user,
    delete_cost,
    get_cost_stats,
)
from fastapi import HTTPException, status
from app.exceptions.cost_exceptions import CostTypeNotFoundException, CostNotFoundException, CostAlreadyExistsException

router = APIRouter(prefix="/costs", tags=["Costs"])


def require_admin(current_user: User) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Requires ADMIN role.",
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
    try:
        require_admin(current_user)
        return create_cost_type(db, data, current_user.id)
    except CostAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


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
    try:
        return add_cost_to_a_user(db, data, current_user.id)
    except CostTypeNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/types/{cost_type_id}", status_code=204)
def delete_cost_type_endpoint(
    cost_type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        require_admin(current_user)
        delete_cost_type(db, cost_type_id)
    except CostTypeNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{cost_id}", status_code=204)
def delete_cost_endpoint(
    cost_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        delete_cost(db, cost_id, current_user.id)
    except CostNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/stats")
def get_cost_stats_endpoint(
    period: str = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_cost_stats(db, current_user.id, period)
