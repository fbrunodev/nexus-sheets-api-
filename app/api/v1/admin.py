from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.repositories.user import ActivationKeyRepository
from app.schemas.admin import ActivationKeyCreate, ActivationKeyResponse
from app.services.admin import list_activation_keys, create_activation_key
from fastapi import HTTPException, status
from app.exceptions.user_exceptions import ActivationKeyGenerationException

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Requires ADMIN role.",
        )
    return current_user


@router.get("/keys", response_model=list[ActivationKeyResponse])
def get_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return list_activation_keys(db)


@router.post("/keys", response_model=ActivationKeyResponse, status_code=201)
def create_key(
    data: ActivationKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key_repo = ActivationKeyRepository(db)
    require_admin(current_user)
    try:
        return create_activation_key(key_repo, db, data)
    except ActivationKeyGenerationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
