import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class CostType(Base):
    __tablename__ = "cost_types"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    costs: Mapped[list["Cost"]] = relationship("Cost", back_populates="cost_type")


class Cost(Base):
    __tablename__ = "costs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cost_type_id: Mapped[str] = mapped_column(String, ForeignKey("cost_types.id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    cost_type: Mapped["CostType"] = relationship("CostType", back_populates="costs")
