from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.sheet import Sheet
from app.schemas.sheet import(
    SheetCreate,
    SheetUpdate,
    SheetResponse,
    SheetLineUpdate,
    SheetLineResponse,
)

from app.services.sheet import (
    list_sheets,
    get_sheet,
    create_new_sheet,
    update_existing_sheet,
    finish_sheet,
    delete_sheet,
    update_line,
    count_sheets,
    get_sheets_stats,
)
from app.services.sheet import add_lines, remove_line, clear_all_lines


# Agrupa todos os endpoints de planilha sob o prefixo /sheets
router = APIRouter(prefix="/sheets", tags=["Sheets"])


@router.get("/")
def get_sheets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str = Query(None),
    search: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = list_sheets(db, current_user.id, limit, offset, status or None, search or None)
    total = count_sheets(db, current_user.id, status or None, search or None)

    return {
        "items": [SheetResponse.model_validate(s) for s in items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }

    
@router.get("/stats")
def get_stats(
    period: str = Query(default="all", description="Período: all, month, week, today"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna estatísticas gerais das planilhas do usuário:
    contadores por status e total geral consolidado.
    """
    return get_sheets_stats(db, current_user.id, period)

@router.post("/", response_model=SheetResponse, status_code=201)
def create_sheet(
    data: SheetCreate,
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cria uma nova planilha com linhas iniciais vazias.
    O número de linhas é definido pelo campo initial_lines.
    """

    return create_new_sheet(db,data, current_user.id)


@router.get("/operator-sheets")
def get_operator_sheets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna planilhas de todos os operadores vinculados ao usuário autenticado."""
    from app.models.user import UserRole
    operators = db.query(User).filter(User.owner_id == current_user.id, User.role == UserRole.OPERADOR).all()
    operator_ids = [op.id for op in operators]

    if not operator_ids:
        return {"items": [], "total": 0, "operators": []}

    sheets = db.query(Sheet).filter(
        Sheet.owner_id.in_(operator_ids),
        Sheet.is_deleted == False
    ).order_by(Sheet.created_at.desc()).offset(offset).limit(limit).all()

    total = db.query(func.count(Sheet.id)).filter(
        Sheet.owner_id.in_(operator_ids),
        Sheet.is_deleted == False
    ).scalar()

    operator_map = {op.id: (op.name or op.email) for op in operators}

    return {
        "items": [{"sheet": SheetResponse.model_validate(s), "operator_name": operator_map.get(s.owner_id, "?")} for s in sheets],
        "total": total,
        "operators": [{"id": op.id, "name": op.name or op.email} for op in operators]
    }


@router.get("/{sheet_id}", response_model=SheetResponse)
def get_sheet_by_id(
    sheet_id:str,
    db: Session =Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna os dados completos de uma planilha incluindo todas as linhas.
    lança 404 se não encontrada ou não pertencer ao usuário
    """
    return get_sheet(db, sheet_id, current_user.id)
    
@router.patch("/{sheet_id}", response_model=SheetResponse)
def update_sheet(
    sheet_id: str,
    data: SheetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Atualiza os dados de uma planilha existente.
    Apenas os campos enviados são atualizados.
    """
    return update_existing_sheet(db, sheet_id, data, current_user.id)


@router.post("/{sheet_id}/finish", response_model=SheetResponse)
def finish_sheet_endpoint(
    sheet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    """
    Finaliza uma planilha - muda o status para FINISHED.
    Após finalizada não pode mais ser editada.
    """

    return finish_sheet(db, sheet_id, current_user.id)


@router.delete("/{sheet_id}", status_code=204)
def delete_sheet_endpoint(
    sheet_id: str,
    db: Session = Depends(get_db),
    current_user: User =Depends(get_current_user),
):
    """
    Realiza o soft delete de uma planilha.
    O registro permanece no banco mas não aparece nas listagens.
    """
    delete_sheet(db, sheet_id, current_user.id)

@router.patch("/{sheet_id}/lines/{line_id}", response_model=SheetLineResponse)
def update_line_endpoint(
    sheet_id:str,
    line_id:str,
    data: SheetLineUpdate,
    db: Session = Depends(get_db),
    current_user:  User = Depends(get_current_user),
):
    """
    Atualiza os valores de uma linha da planilha.
    Recalcula o resultado automaticamente após a atualização.
    Bloqueia edição se a planilha estiver finalizada.
    """

    return update_line(db, sheet_id, line_id, data, current_user.id)



@router.post("/{sheet_id}/lines", response_model=SheetResponse)
def add_lines_endpoint(
    sheet_id: str,
    quantity: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Adiciona N linhas vazias à planilha (padrão 5).
    Use ?quantity=N para definir a quantidade.
    """
    return add_lines(db, sheet_id, current_user.id, quantity)


@router.delete("/{sheet_id}/lines/{line_id}", response_model=SheetResponse)
def remove_line_endpoint(
    sheet_id: str,
    line_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove uma linha específica da planilha.
    """
    return remove_line(db, sheet_id, line_id, current_user.id)


@router.post("/{sheet_id}/clear", response_model=SheetResponse)
def clear_lines_endpoint(
    sheet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Zera os valores de todas as linhas da planilha.
    """
    return clear_all_lines(db, sheet_id, current_user.id)