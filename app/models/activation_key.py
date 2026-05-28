import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

# Importa o enum de tipo de plano diretamente do model User
# evitando duplicação e conflito de enums no SQLAlchemy
from app.models.user import PlanType


class ActivationKey(Base):
    """
    Modelo de chaves de ativação do sistema.
    Cada chave é gerada pelo admin e usada uma única vez
    pelo usuário no momento do registro.
    """
    __tablename__ = "activation_keys"

    # Identificador único universal
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # A chave em si — ex: NX-9DK2-XQ7P-AB12
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Tipo da chave — reutiliza o mesmo enum de PlanType do User
    type: Mapped[PlanType] = mapped_column(
        SAEnum(PlanType), nullable=False
    )

    # Data de expiração — nulo para chaves vitalícias
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Indica se a chave já foi utilizada
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ID do usuário que usou a chave — nulo até ser utilizada
    used_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )

    # Data de criação da chave
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )