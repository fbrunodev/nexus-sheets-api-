import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum



# Enum de roles do sistema - define os níveis de acesso dos usuários
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    OPERADOR = "OPERADOR",
    USER = "USER"



# Enum de tipos de plano - define o tipo de acesso do usuário
class PlanType(str, enum.Enum):
    LIFETIME = "LIFETIME",
    MONTHLY = "MONTHLY",
    TRIAL = "TRIAL"


class User(Base):
    """
    Modelo principal de usuário do sistema.
    Armazena credenciais, role e informações de plano.
    """
    __tablename__ = "users"


    # Identificador único do usuário - evita IDs sequenciais expostos na API
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Email do usuário - usado para login e comunicação
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    

    # Senha armazenada como hash bcrypt - nunca em texto puro
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role do usuário - define permissões e acesso a recursos
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), default= UserRole.USER, nullable=False
    )


    # Indica se a conta foi ativada via activation key
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


    # Tipo de plano contratado
    plan_type: Mapped[PlanType] = mapped_column(
        SAEnum(PlanType), nullable=True
    )

    # Data de expiração do plano — nulo para planos vitalícios
    plan_expires_at: Mapped[datetime] = mapped_column("plan_expiration", DateTime, nullable=True)


    # Data de criação do registro
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable= False
    )

    # Último login - útil para auditoria e segurança
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)
