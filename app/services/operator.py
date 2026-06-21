from sqlalchemy.orm import Session
from app.models.user import User, UserRole, PlanType
from app.schemas.operator import OperatorCreate
from app.repositories.user import get_user_by_email, create_user
from app.core.security import hash_password
from fastapi import HTTPException, status
import uuid


def list_operators(db: Session, owner_id: str) -> list[User]:
    """Retorna todos os operadores criados por um admin/supervisor."""
    return (
        db.query(User)
        .filter(User.role == UserRole.OPERADOR, User.owner_id == owner_id)
        .order_by(User.created_at.desc())
        .all()
    )


def create_operator(db: Session, data: OperatorCreate, owner_id: str) -> User:
    """
    Cria um novo operador vinculado ao admin/supervisor que o criou.
    Conta já ativa, sem necessidade de activation key.
    """
    existing = get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado."
        )

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

    return create_user(db, new_operator)


def delete_operator(db: Session, operator_id: str, owner_id: str) -> None:
    """
    Remove um operador. Só o admin/supervisor que o criou pode deletar.
    """
    operator = (
        db.query(User)
        .filter(
            User.id == operator_id,
            User.role == UserRole.OPERADOR,
            User.owner_id == owner_id,
        )
        .first()
    )
    if not operator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operador não encontrado."
        )
    db.delete(operator)
    db.commit()
