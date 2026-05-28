from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.operator import OperatorCreate
from app.repositories.user import get_user_by_email, create_user
from app.core.security import hash_password
from fastapi import HTTPException, status
import uuid


def list_operators(db: Session) -> list[User]:
    """
    Retorna todos os usuários com role OPERADOR.
    Usado para popular o dropdown de operadores nas planilhas.
    """
    return (
        db.query(User)
        .filter(User.role == UserRole.OPERADOR)
        .order_by(User.created_at.desc())
        .all()
    )


def create_operator(db: Session, data: OperatorCreate) -> User:
    """
    Cria um novo operador no sistema.
    Operadores são criados diretamente pelo admin ou supervisor
    sem precisar de activation key.
    """

    # Verifica se o email já está cadastrado
    existing = get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado."
        )

    # Cria o usuário com role OPERADOR e conta já ativa
    new_operator = User(
        id=str(uuid.uuid4()),
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.OPERADOR,
        is_active=True,
    )

    return create_user(db, new_operator)