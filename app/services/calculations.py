

def calc_line_result(line) -> float:
    """Resultado de uma linha: saque − depósito + baú + bônus.
    Salário e custos não entram aqui (pertencem à planilha/período)."""
    return (
        (line.withdrawal or 0)
        - (line.deposit or 0)
        + (line.chest or 0)
        + (line.bonus or 0)
    )


def calc_sheet_result(sheet) -> float:
    """Resultado de uma planilha: soma das linhas + salário (exceto BAU).
    Custos não entram aqui (pertencem ao período/dono)."""
    lines_total = sum(calc_line_result(line) for line in (sheet.lines or []))
    # cooperation_type is a str enum; comparing with "BAU" works for both the
    # ORM model (CooperationType.BAU == "BAU") and plain strings.
    salary = (sheet.salary or 0) if sheet.cooperation_type != "BAU" else 0
    # Numeric(10,2) columns return Decimal from PostgreSQL; coerce to float.
    return float(lines_total) + float(salary)