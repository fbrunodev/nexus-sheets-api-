from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from app.services.auth import register_user, login_user
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.core.security import create_access_token
from app.repositories.user import UserRepository, ActivationKeyRepository
from app.exceptions.user_exceptions import (
    UserEmailAlreadyExistsException,
    UserExpiredPlanException,
    UserInactiveAccountException,
    UserInvalidCredentialsException,
    InvalidKeyException,
    KeyAlreadyUsedException,
    KeyExpiredException,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register( data: UserRegisterRequest, db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    key_repo = ActivationKeyRepository(db)

    try:
        user = register_user(user_repo, key_repo, db, data)
        access_token = create_access_token(data={"sub": user.id})
        return {"access_token": access_token, "token_type": "bearer", "user": user}
    except UserEmailAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidKeyException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except KeyAlreadyUsedException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except KeyExpiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
def login( data: UserLoginRequest, db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    try:
        return login_user(user_repo, db, data)
    except UserInvalidCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except UserInactiveAccountException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except UserExpiredPlanException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
