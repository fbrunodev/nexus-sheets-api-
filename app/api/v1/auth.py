from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from app.services.auth import register_user, login_user
from app.auth.dependencies import get_current_user
from app.models.user import User

# Cria o roteador - agrupa todos os endpoints de autenticação
# sob o prefixo /auth

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Endpoint de registro de novo usuário.
    Requer email, senha e chave de ativação válida.
    Retorna o token JWT e os dados do usuário criado.
    """

    user = register_user(db, data)

    # Gera o token imediatamente após o registro
    # para o usuário já entrar autenticado
    from app.core.security import create_access_token
    access_token = create_access_token(data={"sub": user.id})


    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }

@router.post("/login", response_model=TokenResponse)
def login(data: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint de login.
    Requer email e senha.
    Retorna o token JWT e os dados do usuário.s
    """

    return login_user(db, data)



@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """
    Endpoint que retorna os dados do usuário autenticado.
    Requer token JWT no header Authorization
    """

    return current_user