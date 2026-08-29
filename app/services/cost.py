from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.cost import Cost, CostType
from app.schemas.cost import CostCreate, CostTypeCreate
import uuid
from app.exceptions.cost_exceptions import (
    CostAlreadyExistsException,
    CostNotFoundException,
    CostTypeNotFoundException,
)
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def list_cost_types(db: Session) -> list[CostType]:
    return db.query(CostType).order_by(CostType.name).all()


def create_cost_type(db: Session, data: CostTypeCreate, admin_id: str) -> CostType:
    logger.info("Attempting to create cost type")

    existing = db.query(CostType).filter(CostType.name == data.name).first()
    if existing:
        logger.warning("Cost type already exists.")
        raise CostAlreadyExistsException("Cost type already exists.")

    cost_type = CostType(
        id=str(uuid.uuid4()),
        name=data.name,
        created_by=admin_id,
    )
    db.add(cost_type)
    db.commit()
    db.refresh(cost_type)
    logger.info(f"Cost type {cost_type.id} created")
    return cost_type


def list_costs(db: Session, owner_id: str, month: int, year: int) -> list[Cost]:
    return (
        db.query(Cost)
        .filter(Cost.owner_id == owner_id, Cost.month == month, Cost.year == year)
        .order_by(Cost.created_at.desc())
        .all()
    )


def delete_cost_type(db: Session, cost_type_id: str):
    logger.info("Attempting to delete cost type")

    cost_type = db.query(CostType).filter(CostType.id == cost_type_id).first()
    if not cost_type:
        logger.warning("Cost type not found.")
        raise CostTypeNotFoundException("Cost type not found.")

    db.delete(cost_type)
    db.commit()
    logger.info(f"Cost type {cost_type_id} deleted")


def add_cost_to_a_user(db: Session, data: CostCreate, owner_id: str) -> Cost:
    logger.info("Attempting to add cost")

    cost_type = db.query(CostType).filter(CostType.id == data.cost_type_id).first()
    if not cost_type:
        logger.warning("Cost type not found.")
        raise CostTypeNotFoundException("Cost type not found.")

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
    logger.info(f"Cost {cost.id} added for owner {owner_id}")
    return cost


def delete_cost(db: Session, cost_id: str, owner_id: str) -> None:
    logger.info("Attempting to delete cost")

    cost = db.query(Cost).filter(Cost.id == cost_id, Cost.owner_id == owner_id).first()
    if not cost:
        logger.warning("Cost not found.")
        raise CostNotFoundException("Cost not found.")

    db.delete(cost)
    db.commit()
    logger.info(f"Cost {cost_id} deleted")


def get_total_costs(db: Session, owner_id: str, month: int | None, year: int | None) -> float:
    query = db.query(func.coalesce(func.sum(Cost.value), 0)).filter(Cost.owner_id == owner_id)
    if month is not None and year is not None:
        query = query.filter(Cost.month == month, Cost.year == year)
    return float(query.scalar())


def get_cost_stats(db: Session, owner_id: str, period: str):
    now = datetime.utcnow()

    query = (
        db.query(CostType.name, func.sum(Cost.value).label("total"))
        .join(Cost, Cost.cost_type_id == CostType.id)
        .filter(Cost.owner_id == owner_id)
    )

    if period == "all":
        pass
    elif period == "today":
        # Filters by creation timestamp — not by the month/year fields — because
        # "today" refers to when the cost was entered, not its billing period.
        query = query.filter(Cost.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    elif period == "month":
        # Uses explicit month/year fields so retroactively registered costs are included.
        query = query.filter(Cost.year == now.year, Cost.month == now.month)
    elif period == "week":
        query = query.filter(Cost.created_at >= now - timedelta(days=7))

    results = query.group_by(CostType.name).all()
    return [{"name": r.name, "value": float(r.total)} for r in results]
