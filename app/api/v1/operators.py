from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.operator import OperatorCreate, OperatorResponse
from app.services.operator import list_operators, create_operator, delete_operator
from fastapi import HTTPException

router = APIRouter(prefix="/operators", tags=["Operators"])


def require_admin_or_supervisor(current_user: User) -> User:
    if current_user.role == UserRole.OPERADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operadores não podem criar outros operadores."
        )
    return current_user


@router.get("/", response_model=list[OperatorResponse])
def get_operators(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista os operadores criados pelo usuário autenticado."""
    return list_operators(db, current_user.id)


@router.post("/", response_model=OperatorResponse, status_code=201)
def create_new_operator(
    data: OperatorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria um novo operador. Requer role ADMIN ou SUPERVISOR."""
    require_admin_or_supervisor(current_user)
    return create_operator(db, data, current_user.id)


@router.delete("/{operator_id}", status_code=204)
def delete_operator_endpoint(
    operator_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove um operador. Só o criador pode remover."""
    require_admin_or_supervisor(current_user)
    delete_operator(db, operator_id, current_user.id)
