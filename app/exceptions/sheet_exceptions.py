

class SheetNotFoundException(Exception):
    """Exceção lançada quando uma planilha não é encontrada."""
    pass

class SheetAlreadyFinishedException(Exception):
    """Exceção lançada quando uma planilha já finalizada é tentada ser editada."""
    pass





#---------------------------SHEET LINES--------------------------------------

class SheetLineNotFoundException(Exception):
    pass