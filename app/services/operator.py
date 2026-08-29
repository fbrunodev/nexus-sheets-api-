from sqlalchemy.orm import Session
from app.models.user import User, UserRole, PlanType
from app.schemas.operator import OperatorCreate
from app.repositories.user import UserRepository
from app.core.security import hash_password
import uuid
from app.exceptions.user_exceptions import UserEmailAlreadyExistsException, OperatorNotFoundException
import logging

logger = logging.getLogger(__name__)


def list_operators(user_repo: UserRepository, owner_id: str) -> list[User]:
    return user_repo.get_operator_by_owner(owner_id)

    
def create_operator(user_repo: UserRepository, db: Session, data: OperatorCreate, owner_id: str) -> User:
    logger.info("Attempting to create operator")

    existing = user_repo.get_user_by_email(data.email)
    if existing:
        logger.warning("Email already exists.")
        raise UserEmailAlreadyExistsException("Email already exists.")

    # Operators are created active with a LIFETIME plan — no activation key required.
    new_operator = User(
        id=str(uuid.uuid4()),
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.OPERADOR,
        is_active=True,
        plan_type=PlanType.LIFETIME,
        owner_id=owner_id,
    )

    user_repo.create_user(new_operator)
    db.commit()
    db.refresh(new_operator)
    logger.info(f"Operator {new_operator.id} created")
    return new_operator


def soft_delete_operator(user_repo: UserRepository, db: Session, operator_id: str, owner_id: str) -> None:
    logger.info("Attempting to delete operator")

    operator = user_repo.get_operator_by_id(operator_id, owner_id)
    logger.info(f"operator {operator_id}")
    if not operator:
        logger.warning("Operator not Found.")
        raise OperatorNotFoundException("Operator not found.")
    operator.is_active = False
    user_repo.update_user(operator)
    db.commit()
    logger.info(f"Operator {operator_id} deleted")
