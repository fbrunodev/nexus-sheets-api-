

def calc_line_result(line) -> float:
    """Resultado de uma linha: saque − depósito + baú + bônus.
    Salário e custos não entram aqui (pertencem à planilha/período)."""
    return (
        (line.withdrawal or 0)
        - (line.deposit or 0)
        + (line.chest or 0)
        + (line.bonus or 0)
    )