from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
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
)



# Agrupa todos os endpoints de planilha sob o prefixo /sheets
router = APIRouter(prefix="/sheets", tags=["Sheets"])


@router.get("/",  response_model=list[SheetResponse])
def get_sheets(
    db: Session = Depends(get_db),
    current_user: User =Depends(get_current_user),
):
    
    """
    Lista todas as planilhas do usuário autenticado.
    Exclui planilhas deletadas automaticamente
    """

    return list_sheets(db, current_user.id)


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



    