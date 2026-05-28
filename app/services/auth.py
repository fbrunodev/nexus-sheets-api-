from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.user import User, PlanType
from app.schemas.user import UserRegisterRequest, UserLoginRequest
from app.repositories.user import (
    get_user_by_email,
    create_user,
    update_user,
    get_activation_key,
    mark_key_as_used
)

from app.core.security import hash_password, verify_password, create_access_token
from fastapi import HTTPException, status


# -----------REGISTRO-------------------------------------------

def register_user(db: Session, data: UserRegisterRequest) -> User:
    """
    Regra de negócio completa do registro do usuário.
    Valida email, chave de ativação, cria usuário e ativa a conta
    """

    # Verifica se o email já esta cadastrado
    existing_user = get_user_by_email(db, data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists."
        )
    
    # Busca a chave de ativação no banco
    activation_key = get_activation_key(db, data.activation_key)

    # Valida se a chave existe
    if not activation_key: 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Key."
        )
    
    # Valida se a chave já foi utilizada
    if activation_key.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="key already exists."
        )
    
    # Valida se a chave não está expirada
    if activation_key.expires_at and activation_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail = "Key expired."
        )
    
    # Define a data de expiração do plano com base no tipo da chave
    plan_expires_at = None
    if activation_key.type == PlanType.MONTHLY:
        # Plano mensal expira em 30 dias a partir de hoje
        plan_expires_at = datetime.utcnow() + timedelta(days=30)
    elif activation_key.type == PlanType.TRIAL:
        # Plano trial expira em 7 dias a partir de hoje
        plan_expires_at = datetime.utcnow() + timedelta(days=7)
    
    # LIFETIME não tem expiração - plan_expires_at permanece None


    # Cria o objeto User com os dados validados
    new_user = User(
        email = data.email,
        password_hash =hash_password(data.password),
        is_active=True, # Ativado imediatamente após validar a chave
        plan_type = activation_key.type,
        plan_expires_at = plan_expires_at,
    )

    # Persiste o usuário no banco
    created_user = create_user(db, new_user)

    # Marca a chave como utilizada vinculando ao usuário criado
    mark_key_as_used(db, activation_key, created_user.id)

    return created_user


def login_user(db: Session, data: UserLoginRequest) -> dict:
    """
    Regra de negócio completa do login.
    Valida credenciais e retorna o token JWT
    """

    # Busca o usuário pelo email
    user = get_user_by_email(db, data.email)

    # Valida se o usuário existe e a senha está correta
    # A mensagem é genérica intecionalmente - não reveal
    # se o email existe ou não no sistema(segurança)

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = " Invalid Credentials."
        )
    

    # Valida se a conta está ativa
    if not  user.is_active:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Inactive account."
        )
    
    # Atualiza o último login do usuário
    user.last_login =  datetime.utcnow()
    update_user(db, user)


    # Gera o token JWT com o ID do usuário como subject
    access_token = create_access_token(data={"sub": user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }