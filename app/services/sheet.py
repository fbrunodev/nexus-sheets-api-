from sqlalchemy import func, case
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.sheet import Sheet, SheetLine, SheetStatus, CooperationType
from app.schemas.sheet import SheetCreate, SheetUpdate, SheetLineUpdate
from app.services.cost import get_total_costs
from app.services.push import send_push_to_user
from app.models.user import User, UserRole
from app.repositories.sheet import(
    get_sheets_by_owner,
    get_sheet_by_id,
    create_sheet,
    update_sheet,
    soft_delete_sheet,
    get_line_by_id,
    update_sheet_line,
    bulk_create_lines,
    count_sheets_by_owner,
)

from fastapi import HTTPException, status
import uuid

def _recalculate_status(sheet: Sheet) -> None:
    """
    Atualiza o status da planilha com base no preenchimento.
    - Sem nenhuma linha preenchida: NOT_STARTED
    - Com pelo menos uma linha preenchida: IN_PROGRESS
    Não altera planilhas FINISHED (status final, definido manualmente).
    """
    # Planilha finalizada não muda de status automaticamente
    if sheet.status == SheetStatus.FINISHED:
        return

    has_data = any(
        line.deposit > 0 or line.withdrawal > 0 or line.chest > 0
        for line in sheet.lines
    )

    sheet.status = SheetStatus.IN_PROGRESS if has_data else SheetStatus.NOT_STARTED

#-------------PLANILHAS--------------------------------------------

def list_sheets(
    db: Session, owner_id: str, limit: int = 10, offset: int = 0,
    status: str | None = None, search: str | None = None,
) -> list[Sheet]:
    return get_sheets_by_owner(db, owner_id, limit, offset, status, search)


def count_sheets(
    db: Session, owner_id: str,
    status: str | None = None, search: str | None = None,
) -> int:
    return count_sheets_by_owner(db, owner_id, status, search)


def get_sheet(db: Session, sheet_id:str, owner_id:str) -> Sheet:
    """
    Busca uma planilha pelo ID.
    Lança 404 se não encontrada ou não pertencer ao usuário.
    """

    sheet = get_sheet_by_id(db, sheet_id, owner_id)

    if not sheet:
        # Verifica se o usuário é admin/dono do operador que criou a planilha
        sheet = db.query(Sheet).filter(Sheet.id == sheet_id, Sheet.is_deleted == False).first()
        if sheet:
            sheet_owner = db.query(User).filter(User.id == sheet.owner_id).first()
            if not sheet_owner or sheet_owner.owner_id != owner_id:
                sheet = None

    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not Found."
        )

    return sheet

def create_new_sheet(db: Session, data: SheetCreate, owner_id:str) -> Sheet:
    """
    Cria uma nova planilha com linhas iniciais vazias.
    O número de linhas é definido por data.initial_lines.
    """

    # Cria o objeto planilha

    new_sheet = Sheet(
        id=str(uuid.uuid4()),
        name=data.name,
        owner_id=owner_id,
        operator_id=data.operator_id,
        goal=data.goal,
        platform_id=data.platform_id,
        cooperation_type=data.cooperation_type or CooperationType.META,
    )

    # Persiste a planilha primeiro para ter o ID disponível
    created_sheet = create_sheet(db, new_sheet)

    # Se vieram depósitos colados, cria uma linha para cada valor
    # Caso contrário, cria linhas vazias conforme initial_lines
    if data.deposits:
        lines = [
            SheetLine(
                id=str(uuid.uuid4()),
                sheet_id=created_sheet.id,
                line_number=i + 1,
                deposit=deposit,
                withdrawal=0,
                chest=0,
                # Resultado inicial: saque(0) + baú(0) - depósito
                result=-deposit,
            )
            for i, deposit in enumerate(data.deposits)
        ]
    else:
        lines = [
            SheetLine(
                id=str(uuid.uuid4()),
                sheet_id=created_sheet.id,
                line_number=i + 1,
                deposit=0,
                withdrawal=0,
                chest=0,
                result=0,
            )
            for i in range(data.initial_lines)
        ]

    bulk_create_lines(db, lines)

   # Recarrega a planilha com as linhas criadas
    db.refresh(created_sheet)

    # Atualiza o status com base no preenchimento (colou depósitos = IN_PROGRESS)
    _recalculate_status(created_sheet)
    update_sheet(db, created_sheet)

    # Notifica admin se o criador for um operador
    sheet_owner = db.query(User).filter(User.id == owner_id).first()
    if sheet_owner and sheet_owner.role == UserRole.OPERADOR and sheet_owner.owner_id:
        operator_name = sheet_owner.name or sheet_owner.email
        deposit_count = len(created_sheet.lines) if data.deposits else 0
        platform_name = created_sheet.name
        if deposit_count > 0:
            msg = f"{operator_name} iniciou {deposit_count} dep na {platform_name}"
        else:
            msg = f"{operator_name} criou uma planilha na {platform_name}"
        send_push_to_user(db, sheet_owner.owner_id, "Nexus Sheets", msg)

    return created_sheet


def update_existing_sheet(
        db: Session, sheet_id: str, data: SheetUpdate, owner_id: str
) -> Sheet:
    """
    Atualiza os dados de uma planilha existente.
    Planilhas finalizadas só podem ser editadas por admins -
    essa validação é feita no endpoint
    """

    sheet = get_sheet(db, sheet_id, owner_id)

    if sheet.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para editar esta planilha.")

    # Atualiza apenas os campos enviados - ignora os nulos
    if data.name is not None:
        sheet.name = data.name
    if data.operator_id is not None:
        sheet.operator_id = data.operator_id
    if data.salary is not None:
        sheet.salary = data.salary
    if data.goal is not None:
        sheet.goal = data.goal


    return update_sheet(db, sheet)


def finish_sheet(db: Session, sheet_id: str, owner_id:str) -> Sheet:
    """
    Finaliza uma planilha - muda o status para FINISHED.
    Após finalizada a planilha não pode ser mais editada
    """

    sheet = get_sheet(db, sheet_id, owner_id)

    if sheet.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para editar esta planilha.")

    # Valida se a planilha já está finalizada

    if sheet.status == SheetStatus.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Planilha já está finalizada"
        )
    
    sheet.status = SheetStatus.FINISHED
    updated = update_sheet(db, sheet)

    total_withdrawal = sum(float(l.withdrawal) for l in sheet.lines)
    total_deposit = sum(float(l.deposit) for l in sheet.lines)
    total_chest = sum(float(l.chest) for l in sheet.lines)
    total_bonus = sum(float(l.bonus) for l in sheet.lines)
    result = total_withdrawal - total_deposit + total_chest + total_bonus + float(sheet.salary)
    result_str = f"+R$ {result:,.2f}" if result >= 0 else f"-R$ {abs(result):,.2f}"
    send_push_to_user(db, sheet.owner_id, "Nexus Sheets", f"{sheet.name} finalizada! Resultado: {result_str}")

    sheet_owner = db.query(User).filter(User.id == sheet.owner_id).first()
    if sheet_owner and sheet_owner.role == UserRole.OPERADOR and sheet_owner.owner_id:
        operator_name = sheet_owner.name or sheet_owner.email
        admin_message = f"{operator_name} finalizou {sheet.name}! Resultado: {result_str}"
        send_push_to_user(db, sheet_owner.owner_id, "Nexus Sheets", admin_message)

    return updated


def delete_sheet(db: Session, sheet_id: str, owner_id: str) -> None:
    """Realiza o soft delete de uma planilha"""
    sheet = get_sheet(db, sheet_id, owner_id)
    soft_delete_sheet(db,sheet)

# ----LINHAS-----------------------------------

def update_line(
        db: Session, sheet_id: str, line_id: str, data: SheetLineUpdate, owner_id: str

) -> SheetLine:
    """
    Atualiza uma linha da planilha e recalcula o resultado.
    valida se a planilha pertence ao usuário e não está finalizadas
    """

    # Garante que a planilha existe e pertence ao usuário
    sheet = get_sheet(db, sheet_id, owner_id)

    if sheet.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para editar esta planilha.")

    # Bloqueia edição de planilhas finalizadas
    if sheet.status == SheetStatus.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Planilha Finalizada não pode ser editada"
        )
    

    # Busca a linha
    line = get_line_by_id(db, line_id, sheet_id)
    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Line not Found."
        )
    
    # Atualiza apenas os campos enviados
    if data.deposit is not None:
        line.deposit = data.deposit
    if data.withdrawal is not None:
        line.withdrawal = data.withdrawal
    if data.chest is not None:
        line.chest = data.chest
    if data.bonus is not None:
        line.bonus = data.bonus

    updated_line = update_sheet_line(db, line)

    # Recalcula o status da planilha após editar a linha
    db.refresh(sheet)
    _recalculate_status(sheet)
    update_sheet(db, sheet)

    return updated_line



# ─── GERENCIAMENTO DE LINHAS EM MASSA ─────────────────────────

def add_lines(db: Session, sheet_id: str, owner_id: str, quantity: int) -> Sheet:
    """
    Adiciona N novas linhas vazias ao final da planilha.
    A numeração continua a partir da última linha existente.
    """
    sheet = get_sheet(db, sheet_id, owner_id)

    if sheet.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para editar esta planilha.")

    # Bloqueia edição de planilhas finalizadas
    if sheet.status == SheetStatus.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Planilha finalizada não pode ser editada."
        )

    # Descobre o maior número de linha atual
    last_number = max((line.line_number for line in sheet.lines), default=0)

    # Cria as novas linhas
    new_lines = [
        SheetLine(
            id=str(uuid.uuid4()),
            sheet_id=sheet_id,
            line_number=last_number + i + 1,
            deposit=0,
            withdrawal=0,
            chest=0,
            result=0,
        )
        for i in range(quantity)
    ]

    bulk_create_lines(db, new_lines)
    db.refresh(sheet)
    return sheet


def remove_line(db: Session, sheet_id: str, line_id: str, owner_id: str) -> Sheet:
    """
    Remove uma linha específica da planilha.
    Após remover, não renumera as linhas restantes.
    """
    sheet = get_sheet(db, sheet_id, owner_id)

    if sheet.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para editar esta planilha.")

    if sheet.status == SheetStatus.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Planilha finalizada não pode ser editada."
        )

    line = get_line_by_id(db, line_id, sheet_id)
    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linha não encontrada."
        )

    db.delete(line)
    db.commit()
    db.refresh(sheet)

    # Recalcula o status após remover a linha
    _recalculate_status(sheet)
    update_sheet(db, sheet)
    return sheet


def clear_all_lines(db: Session, sheet_id: str, owner_id: str) -> Sheet:
    """
    Zera os valores de todas as linhas da planilha.
    Mantém as linhas, apenas limpa depósito, saque, baú e resultado.
    """
    sheet = get_sheet(db, sheet_id, owner_id)

    if sheet.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para editar esta planilha.")

    if sheet.status == SheetStatus.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Planilha finalizada não pode ser editada."
        )

    # Zera todos os valores de cada linha
    for line in sheet.lines:
        line.deposit = 0
        line.withdrawal = 0
        line.chest = 0
        line.result = 0

    db.commit()
    db.refresh(sheet)

    # Tudo zerado: volta para NOT_STARTED
    _recalculate_status(sheet)
    update_sheet(db, sheet)
    return sheet



def _period_filter(period: str) -> list:
    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return [Sheet.created_at >= start]
    if period == "week":
        return [Sheet.created_at >= now - timedelta(days=7)]
    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return [Sheet.created_at >= start]
    return []


def get_sheets_stats(db: Session, owner_id: str, period: str = "all") -> dict:
    """
    Calcula estatísticas consolidadas via SQL agregado.
    
    Antes: carregava todas as planilhas + linhas na memória (limit=1000000).
    Agora: uma query com JOIN e agregações — muito mais eficiente.
    
    Fórmula por planilha: sum(withdrawal) - sum(deposit) + sum(chest) + salary
    Grand total: soma dos resultados de todas as planilhas do usuário.
    """

    # Subconsulta: agrega os valores das linhas por planilha
    # Usamos coalesce para tratar planilhas sem linhas (retorna 0 em vez de NULL)
    line_agg = (
        db.query(
            SheetLine.sheet_id,
            func.coalesce(func.sum(SheetLine.withdrawal), 0).label("total_withdrawal"),
            func.coalesce(func.sum(SheetLine.deposit), 0).label("total_deposit"),
            func.coalesce(func.sum(SheetLine.chest), 0).label("total_chest"),
            func.coalesce(func.sum(SheetLine.bonus), 0).label("total_bonus"),
        )
        .group_by(SheetLine.sheet_id)
        .subquery()
    )

    # Query principal: JOIN sheets com a subconsulta de linhas
    # Filtra por dono e soft delete, agrega contadores e grand_total
    result = (
        db.query(
            func.count(Sheet.id).label("total"),
            func.sum(
                case((Sheet.status == SheetStatus.NOT_STARTED, 1), else_=0)
            ).label("not_started"),
            func.sum(
                case((Sheet.status == SheetStatus.IN_PROGRESS, 1), else_=0)
            ).label("in_progress"),
            func.sum(
                case((Sheet.status == SheetStatus.FINISHED, 1), else_=0)
            ).label("finished"),
            # Grand total: soma de (withdrawal - deposit + chest + salary) por planilha
            func.coalesce(
                func.sum(
                    func.coalesce(line_agg.c.total_withdrawal, 0)
                    - func.coalesce(line_agg.c.total_deposit, 0)
                    + func.coalesce(line_agg.c.total_chest, 0)
                    + func.coalesce(line_agg.c.total_bonus, 0)
                    + Sheet.salary
                ),
                0,
            ).label("grand_total"),
        )
        .outerjoin(line_agg, Sheet.id == line_agg.c.sheet_id)
        .filter(Sheet.owner_id == owner_id, Sheet.is_deleted == False)
        .filter(*_period_filter(period))
        .one()
    )

    now = datetime.utcnow()
    if period == "all":
        total_costs = get_total_costs(db, owner_id, month=None, year=None)
    else:
        total_costs = get_total_costs(db, owner_id, month=now.month, year=now.year)

    grand_total = float(result.grand_total or 0) - total_costs

    operator_ids = [u.id for u in db.query(User).filter(User.owner_id == owner_id, User.role == UserRole.OPERADOR).all()]
    if operator_ids:
        for op_id in operator_ids:
            op_costs = get_total_costs(db, op_id, month=None, year=None) if period == "all" else get_total_costs(db, op_id, month=now.month, year=now.year)
            op_line_agg = (
                db.query(
                    SheetLine.sheet_id,
                    func.coalesce(func.sum(SheetLine.withdrawal), 0).label("total_withdrawal"),
                    func.coalesce(func.sum(SheetLine.deposit), 0).label("total_deposit"),
                    func.coalesce(func.sum(SheetLine.chest), 0).label("total_chest"),
                    func.coalesce(func.sum(SheetLine.bonus), 0).label("total_bonus"),
                )
                .group_by(SheetLine.sheet_id)
                .subquery()
            )
            op_result = (
                db.query(
                    func.coalesce(
                        func.sum(
                            func.coalesce(op_line_agg.c.total_withdrawal, 0)
                            - func.coalesce(op_line_agg.c.total_deposit, 0)
                            + func.coalesce(op_line_agg.c.total_chest, 0)
                            + func.coalesce(op_line_agg.c.total_bonus, 0)
                            + Sheet.salary
                        ), 0
                    ).label("op_total")
                )
                .outerjoin(op_line_agg, Sheet.id == op_line_agg.c.sheet_id)
                .filter(Sheet.owner_id == op_id, Sheet.is_deleted == False)
                .scalar()
            )
            grand_total += float(op_result or 0) - op_costs

    return {
        "total": result.total or 0,
        "not_started": int(result.not_started or 0),
        "in_progress": int(result.in_progress or 0),
        "finished": int(result.finished or 0),
        "grand_total": grand_total,
    }