from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.repositories.user import get_user_by_id
from app.models.user import User

# Define o esquema de autenticação Bearer Token
# O FastAPI usa isso para exibir o botão "Authorize" no Swagger

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) ->  User:
    """
    Dependência que extrai e valida o token JWT do header Authorization.
    Usada em qualquer endpoint que requer autenticação.

    Fluxo:
    1. Extrai o token do header Authorization> Bearer <token>
    2. Decodifica e valida o JWT
    3. Busca o usuário no banco pelo ID contido no token
    4. Retorna o usuário autenticado ou lança 401
    """


    # Decodifica o token - retorna None se inválido ou expirado
    payload = decode_access_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail="Expired or Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extrai o ID do usuário do payload do token
    user_id: str = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Busca o usuário no banco
    user = get_user_by_id(db, user_id)


    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not Found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Valida se a conta ainda está ativa
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account.",
        )
    
    return user