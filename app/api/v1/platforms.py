from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.platform import PlatformCreate, PlatformResponse
from app.services.platform import list_platforms, create_new_platform, remove_platform
from app.repositories.platform import PlatformRepository
from app.exceptions.platform_exceptions import (
    PlatformNotFoundException,
    PlatformAlreadyExistsException,
    PlatformNameEmptyException,
)
from fastapi import HTTPException

router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.get("/", response_model=list[PlatformResponse])
def get_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    platform_repo = PlatformRepository(db)
    return list_platforms(platform_repo)


@router.post("/", response_model=PlatformResponse, status_code=status.HTTP_201_CREATED)
def create_platform_endpoint(
    data: PlatformCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    platform_repo = PlatformRepository(db)
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can create platforms.")

    try:
        return create_new_platform(platform_repo, db, data.name)
    except PlatformNameEmptyException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PlatformAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform_endpoint(
    platform_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    platform_repo = PlatformRepository(db)
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can remove platforms.")

    try:
        remove_platform(platform_repo, db, platform_id)
    except PlatformNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
