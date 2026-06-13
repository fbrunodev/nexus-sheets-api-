import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


# Enum de Status da planilha - controla o ciclo de vida da operação
class SheetStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"

class Sheet(Base):
    """
    Modelo de planilha operacional.
    Cada planilha representa uma sessão/operação completa
    Contém linhas operacionais, custos e resultado final

    """

    __tablename__ = "sheets"


    # Identificador único universal
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())

    )


    # Nome da Planilha
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Meta da planilha — objetivo numérico a atingir (valor inteiro)
    goal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Dono da planilha - usuário que criou
    owner_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )

    # Operador vinculado á planilha - pode ser nulo inicialmente
    operator_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )

    # Status atual da planilha
    status: Mapped[SheetStatus] = mapped_column(
        SAEnum(SheetStatus), default=SheetStatus.NOT_STARTED, nullable=False
    )


    # ------------CUSTOS----------------------------------------------------
    # Cada custo é opcional - zerado por padrão

    cost_proxy :Mapped[float] = mapped_column(Numeric(10,2), default =0, nullable=False)
    cost_sms: Mapped[float] = mapped_column(Numeric(10,2), default =0, nullable=False)
    cost_bot : Mapped[float] = mapped_column(Numeric(10,2), default =0, nullable=False)
    cost_fintech : Mapped[float] = mapped_column(Numeric(10,2), default =0, nullable=False)


    # Salario

    salary: Mapped[float] = mapped_column(Numeric(10,2), default =0, nullable=False)


    # Indica se a planilha foi deletada (soft delete)
    # Registros deletados não aparecem nas listagens mas ficam no banco

    is_deleted : Mapped[bool] = mapped_column( Boolean, default=False, nullable = False)


    # Data de Criação
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), nullable=False
    )


    # Data da última atualização
    updated_at: Mapped[datetime]= mapped_column(
        DateTime,default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


    # Relacionamentos com as linhas da planilha
    # lazy="dynamic" permite filtrar as linhas sem carregar todas na memória

    lines: Mapped[list["SheetLine"]] = relationship(
        "SheetLine", back_populates="sheet", lazy="select", order_by="SheetLine.line_number"
    )   
    # Plataforma vinculada à planilha (opcional)
    platform_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("platforms.id"), nullable=True
    )


class SheetLine(Base):
    """
    Modelo de linha operacional da planilha
    Cada linha representa uma operação individual com
    depósito, saque, baú e resultado calculado
    """

    __tablename__ = "sheet_lines"

    # Identificador único universal
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uiid4())
    )


    # Planilha à qual esta linha pertence
    sheet_id: Mapped[str] = mapped_column(
        String, ForeignKey("sheets.id"), nullable=False
    )

    # Número da linha - posição na planilha (1,2,3...)
    line_number: Mapped[int] = mapped_column(nullable=False)

    # Valor depositado na operação
    deposit: Mapped[float] = mapped_column(Numeric(10,2), default=0, nullable=False)

    # Valor Sacado na operação
    withdrawal: Mapped[float] = mapped_column(Numeric(10,2), default=0, nullable=False)


    # Valor em báu
    chest: Mapped[float] = mapped_column(Numeric(10,2), default=0, nullable=False)

    # Resultado calculado automaticamente: saque + baú - depósito
    result: Mapped[float] = mapped_column(Numeric(10,2), default=0, nullable=False)


    # Data de criação da linha
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default = datetime.utcnow, nullable=False
    )

    # Relacionamento inverso com a planilha
    sheet: Mapped["Sheet"] = relationship("Sheet", back_populates="lines")
