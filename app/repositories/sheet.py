from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.sheet import Sheet, SheetLine
from datetime import datetime, timedelta


def _apply_sheet_filters(query,status=None, search=None, period_filter=None):
    if status:
        query = query.filter(Sheet.status == status)
    if search:
        query = query.filter(Sheet.name.ilike(f"%{search}%"))
    if period_filter: 
        query = query.filter(*period_filter)

    return query


#------------------SHEET----------------------------------------
class SheetRepository:
    def __init__(self, db: Session):
        self.db = db
    


    def get_sheets_by_owner(
            self, owner_id: str, limit: int = 20, offset: int = 0,
            status: str | None = None, search: str | None = None,
            period_filter: list | None = None
    ) -> list[Sheet]:
        
        """Retorna as planilhas ativas de um usuário, paginadas, com filtros opcionais."""
        
        query = self.db.query(Sheet).filter(Sheet.owner_id == owner_id, Sheet.is_deleted == False)
        query = _apply_sheet_filters(query,status,search,period_filter)
        
        return query.order_by(Sheet.created_at.desc()).offset(offset).limit(limit).all()


    def count_sheets_by_owner(
        self, owner_id: str,
        status: str | None = None, search: str | None = None,
        period_filter: list | None = None,
    ) -> int:
        """Conta o total de planilhas ativas do usuário, respeitando os filtros."""
        query = self.db.query(func.count(Sheet.id)).filter(Sheet.owner_id == owner_id, Sheet.is_deleted == False)
        query = _apply_sheet_filters(query, status, search, period_filter)
        return query.scalar()
    
     
    def get_sheet_by_id(self, sheet_id: str, owner_id: str) -> Sheet| None:
        """
        Busca uma planilha pelo ID garantido que pertence ao usuário.
        Evita que um usuário acesse planilhas de outro.
        """
        return self.db.query(Sheet).filter(
            Sheet.id == sheet_id,
            Sheet.owner_id == owner_id,
            Sheet.is_deleted == False
        ).first()

    def create_sheet(self, sheet: Sheet) -> Sheet:
        """Cria uma nova planilha."""
        self.db.add(sheet)
        return sheet

    def update_sheet(self, sheet: Sheet) -> Sheet:
        """Salva alterações em uma planilha existente."""
        sheet.updated_at = datetime.utcnow()
        self.db.add(sheet)
        return sheet



    def soft_delete_sheet(self, sheet: Sheet) -> Sheet:
        """
        Marca a planilha como deletada sem remover do banco.
        Preserva o histórico para auditoria.
        """

        sheet.is_deleted =True
        sheet.updated_at = datetime.utcnow()
        self.db.add(sheet)
        return sheet


#---------------SHEET LINES---------------------------------------

class SheetLineRepository:
    def __init__(self, db: Session):
        self.db = db
        
    
    def get_line_by_id(self, line_id:str, sheet_id: str) -> SheetLine | None:
        """Busca uma linha pelo Id garantido que pertence a planilha"""
        return(
            self.db.query(SheetLine)
            .filter(SheetLine.id == line_id, SheetLine.sheet_id == sheet_id)
            .first()
        )


    def update_sheet_line(self, line: SheetLine) -> SheetLine:
        """
        Salva alterações em uma linha e recalcula o resultado.
        Resultado = saque + baú - depósito
        """

        line.result = float(line.withdrawal) - float(line.deposit) + float(line.chest) + float(line.bonus)
        self.db.add(line)
        return line


    def bulk_create_lines(self, lines: list[SheetLine]) -> list[SheetLine]:
        """
        Cria múltiplas linhas de uma vez - usado na criação inicial da planilha
        Mais eficiente que criar uma por uma
        """

        self.db.add_all(lines)
        return lines
    
    def delete_line(self, line: SheetLine) -> SheetLine:
        
        """
        Deleta uma linha 
        """
        self.db.delete(line)
        self.db.flush()
        return line