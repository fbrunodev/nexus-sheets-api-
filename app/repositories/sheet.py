from sqlalchemy.orm import Session
from app.models.sheet import Sheet, SheetLine, SheetStatus
from datetime import datetime


#------------------SHEET----------------------------------------

def get_sheets_by_owner(
    db:Session, owner_id:str, limit: int=20, offset: int=0
) -> list[Sheet]:
    """
    Retorna as planilhas ativas de um usuário, paginadas.
    Exclui planilhas deletadas (soft delete).

    """

    return (
        db.query(Sheet)
        .filter(Sheet.owner_id == owner_id, Sheet.is_deleted == False)
        .order_by(Sheet.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

def count_sheets_by_owner(db: Session, owner_id: str) -> int:
    """Conta o total de planilhas ativas do usuário (para saber se há mais a carregar)."""
    return(
        db.query(Sheet)
        .filter(Sheet.owner_id == owner_id, Sheet.is_deleted ==False)
        .count()
    )

def get_sheet_by_id(db:Session, sheet_id: str, owner_id: str) -> Sheet| None:
    """
    Busca uma planilha pelo ID garantido que pertence ao usuário.
    Evita que um usuário acesse planilhas de outro.
    """

    return (
        db.query(Sheet)
        .filter(
            Sheet.id == sheet_id,
            Sheet.owner_id == owner_id,
            Sheet.is_deleted == False
        )
        .first()
    )




def create_sheet(db: Session, sheet: Sheet) -> Sheet:
    """Persiste uma nova planilha no banco"""
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    return sheet

def update_sheet(db: Session, sheet: Sheet) -> Sheet:
    """Salva alterações em uma planilha existente."""
    sheet.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sheet)
    return sheet



def soft_delete_sheet(db: Session, sheet: Sheet) -> Sheet:
    """
    Marca a planilha como deletada sem remover do banco.
    Preserva o histórico para auditoria.
    """

    sheet.is_deleted =True
    sheet.updated_at = datetime.utcnow()
    db.commit()
    return sheet


#---------------SHEET LINES---------------------------------------

def create_sheet_line(db:Session, line:SheetLine) -> SheetLine:
    """Persiste uma nova linha de planilha no banco"""
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def get_line_by_id(db: Session, line_id:str, sheet_id: str) -> SheetLine | None:
    """Busca uma linha pelo Id garantido que pertence a planilha"""
    return(
        db.query(SheetLine)
        .filter(SheetLine.id == line_id, SheetLine.sheet_id == sheet_id)
        .first()
    )

def update_sheet_line(db: Session, line: SheetLine) -> SheetLine:
    """
    Salva alterações em uma linha e recalcula o resultado.
    Resultado = saque + baú - depósito
    """

    line.result = float(line.withdrawal) + float(line.chest) - float(line.deposit)
    db.commit()
    db.refresh(line)
    return line


def bulk_create_lines(db: Session, lines: list[SheetLine]) -> list[SheetLine]:
    """
    Cria múltiplas linhas de uma vez - usado na criação inicial da planilha
    Mais eficiente que criar uma por uma
    """

    db.add_all(lines)
    db.commit()
    return lines