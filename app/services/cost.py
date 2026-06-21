from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.cost import Cost, CostType
from app.schemas.cost import CostCreate, CostTypeCreate
import uuid


def list_cost_types(db: Session) -> list[CostType]:
    return db.query(CostType).order_by(CostType.name).all()


def create_cost_type(db: Session, data: CostTypeCreate, admin_id: str) -> CostType:
    existing = db.query(CostType).filter(CostType.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tipo de custo já existe."
        )
    cost_type = CostType(
        id=str(uuid.uuid4()),
        name=data.name,
        created_by=admin_id,
    )
    db.add(cost_type)
    db.commit()
    db.refresh(cost_type)
    return cost_type


def list_costs(db: Session, owner_id: str, month: int, year: int) -> list[Cost]:
    return (
        db.query(Cost)
        .filter(Cost.owner_id == owner_id, Cost.month == month, Cost.year == year)
        .order_by(Cost.created_at.desc())
        .all()
    )


def create_cost(db: Session, data: CostCreate, owner_id: str) -> Cost:
    cost_type = db.query(CostType).filter(CostType.id == data.cost_type_id).first()
    if not cost_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de custo não encontrado."
        )
    cost = Cost(
        id=str(uuid.uuid4()),
        cost_type_id=data.cost_type_id,
        owner_id=owner_id,
        value=data.value,
        month=data.month,
        year=data.year,
        description=data.description,
    )
    db.add(cost)
    db.commit()
    db.refresh(cost)
    return cost


def delete_cost(db: Session, cost_id: str, owner_id: str) -> None:
    cost = db.query(Cost).filter(Cost.id == cost_id, Cost.owner_id == owner_id).first()
    if not cost:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custo não encontrado."
        )
    db.delete(cost)
    db.commit()


def get_total_costs(db: Session, owner_id: str, month: int | None, year: int | None) -> float:
    query = db.query(func.coalesce(func.sum(Cost.value), 0)).filter(Cost.owner_id == owner_id)
    if month is not None and year is not None:
        query = query.filter(Cost.month == month, Cost.year == year)
    result = query.scalar()
    return float(result)
