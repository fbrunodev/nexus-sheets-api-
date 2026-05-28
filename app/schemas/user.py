from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole, PlanType

# ------REQUEST SCHEMAS (dados que entram na API)----------------------------

class UserRegisterRequest(BaseModel):
    """
    Dados necessários para registrar um novo usuário.
    A activation_key é obrigatória - sem ela a conta não é ativada
   """
    
    email: EmailStr
    password: str
    activation_key: str


class UserLoginRequest(BaseModel):
    """
    Dados necessários para autenticas um usuário existente
    
    """
    email: EmailStr
    password: str


#-----------RESPONSE SCHEMAS (dados que saem da API)----------------------------

class UserResponse(BaseModel):
    """
    Dados públicos do usuário retornados pela API.
    Nunca expõe password_hash ou informações sensíveis.
    """
    model_config = {"from_attributes": True}
    
    id: str
    email: str
    role: UserRole
    is_active: bool
    plan_type: Optional[PlanType]
    plan_expires_at: Optional[datetime]
    created_at: datetime
    last_login: Optional[datetime]

    

class TokenResponse(BaseModel):
    """
    Resposta retornada após login bem sucedido.
    Contém o token JWT e o tipo de token.
    """
    access_token: str
    token_type: str="bearer"
    user: UserResponse
