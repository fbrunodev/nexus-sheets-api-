import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    OPERATOR = "OPERATOR"
    USER = "USER"


class PlanType(str, enum.Enum):
    LIFETIME = "LIFETIME"
    MONTHLY = "MONTHLY"
    TRIAL = "TRIAL"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), default=UserRole.USER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    plan_type: Mapped[PlanType] = mapped_column(SAEnum(PlanType), nullable=True)

    # DB column is named "plan_expiration". None for LIFETIME plans.
    plan_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Self-referencing FK: OPERADOR users point to the admin/supervisor who created them.
    owner_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
