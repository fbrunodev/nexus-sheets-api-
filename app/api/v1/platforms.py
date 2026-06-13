from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.platform import PlatformCreate, PlatformResponse
from app.services.platform import list_platforms, create_new_platform, remove_platform
from fastapi import HTTPException


router = APIRouter(prefix="/platforms", tags=["platforms"])

@router.get("/", response_model=list[PlatformResponse])
def get_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
): 

    """Lista todas as plataformas. Qualquer usuário autenticado pode ver."""
    return list_platforms(db)


@router.post("/", response_model=PlatformResponse, status_code=status.HTTP_201_CREATED)
def create_platform_endpoint(
    data: PlatformCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    """Cria uma nova plataforma. Apenas ADMIN."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar plataformas.")
    return create_new_platform(db, data.name)  

@router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform_endpoint(
    platform_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove uma plataforma. Apenas ADMIN."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem remover plataformas.")
    remove_platform(db, platform_id)