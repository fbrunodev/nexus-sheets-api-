from sqlalchemy.orm import Session
from app.models.sheet import Sheet, SheetLine, SheetStatus
from app.schemas.sheet import SheetCreate, SheetUpdate, SheetLineUpdate
from app.repositories.sheet import(
    get_sheets_by_owner,
    get_sheet_by_id,
    create_sheet,
    update_sheet,
    soft_delete_sheet,
    get_line_by_id,
    update_sheet_line,
    bulk_create_lines
)

from fastapi import HTTPException, status
import uuid


#-------------PLANILHAS--------------------------------------------

def list_sheets(db: Session, owner_id: str)-> list[Sheet]:
    """
    Retorna todas as planilhas ativas do usuário
    """
    return get_sheets_by_owner(db, owner_id)

def get_sheet(db: Session, sheet_id:str, owner_id:str) -> Sheet:
    """
    Busca uma planilha pelo ID.
    Lança 404 se não encontrada ou não pertencer ao usuário.
    """

    sheet = get_sheet_by_id(db, sheet_id, owner_id)


    if not sheet:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = " Sheet not Found."
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
    )

    # Persiste a planilha primeiro para ter o ID disponível
    created_sheet = create_sheet(db, new_sheet)

    # Cria as Linhas iniciais vazias
    lines = [
        SheetLine(
            id = str(uuid.uuid4()),
            sheet_id = created_sheet.id,
            line_number = i + 1,
            deposit = 0,
            withdrawal = 0,
            chest = 0,
            result = 0,

        )

        for i in range(data.initial_lines)
    ]


    bulk_create_lines(db,lines)

    # Recarrega a planilha com as linhas criadas
    db.refresh(created_sheet)
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

    # Atualiza apenas os campos enviados - ignora os nulos
    if data.name is not None:
        sheet.name = data.name
    if data.operator_id is not None:
        sheet.operator_id = data.operator_id
    if data.cost_proxy is not None:
        sheet.cost_proxy = data.cost_proxy
    if data.cost_sms is not None:
        sheet.cost_sms = data.cost_sms
    if data.cost_bot is not None:
        sheet.cost_bot = data.cost_bot
    if data.cost_fintech is not None:
        sheet.cost_fintech = data.cost_fintech
    if data.salary is not None:
        sheet.salary = data.salary

    return update_sheet(db, sheet)


def finish_sheet(db: Session, sheet_id: str, owner_id:str) -> Sheet:
    """
    Finaliza uma planilha - muda o status para FINISHED.
    Após finalizada a planilha não pode ser mais editada
    """

    sheet = get_sheet(db, sheet_id, owner_id)

    # Valida se a planilha já está finalizada

    if sheet.status == SheetStatus.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Planilha já está finalizada"
        )
    
    sheet.status = SheetStatus.FINISHED
    return update_sheet(db, sheet)


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

    return update_sheet_line(db, line)