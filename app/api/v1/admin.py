from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.admin import ActivationKeyCreate, ActivationKeyResponse
from app.services.admin import list_activation_keys, create_activation_key
from fastapi import HTTPException, status

# Agrupa todos os endpoints administrativos
router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User) -> User:
    """
    Valida se o usuário autenticado tem role ADMIN.
    Todos os endpoints desse módulo são exclusivos para admins.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Requer role ADMIN."
        )
    return current_user


@router.get("/keys", response_model=list[ActivationKeyResponse])
def get_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista todas as activation keys do sistema.
    Exclusivo para ADMIN.
    """
    require_admin(current_user)
    return list_activation_keys(db)


@router.post("/keys", response_model=ActivationKeyResponse, status_code=201)
def create_key(
    data: ActivationKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gera uma nova activation key.
    Exclusivo para ADMIN.
    """
    require_admin(current_user)
    return create_activation_key(db, data)
