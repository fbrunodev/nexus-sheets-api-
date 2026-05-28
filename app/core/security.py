from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError,jwt
from bcrypt import hashpw, checkpw, gensalt
from app.core.config import settings


#------Senhas---------------------------------


def hash_password(password: str) ->str:
    """
    Gera o hash bcrypt de uma senha em texto puro.
    O gensalt() adiciona um salt aleatório automaticamente,
    tornando cada hash único mesmo para senhas iguais.
    """

    return hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara uma senha em texto puro com o hash armazenado.
    Retorna True se a senha for válida, False caso contrário
    """
    return checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


# ----JWT------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Gera um token JWT assinado com as informações do usuário.
    O token expira em ACCESS_TOKEN_EXPIRE_MINUTES por padrão,
    ou no tempo definido em expires_delta
    """

    to_encode = data.copy()

    # Define o tempo de expiração do token
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    )

    to_encode.update({"exp": expire})

    # Assina o token com a SECRET_KEY usando o algoritmo definido
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)



def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica e valida um token JWT.
    Retorna o payload se válido , None se expirado ou inválido
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None