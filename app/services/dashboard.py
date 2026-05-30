from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.models.sheet import Sheet, SheetLine, SheetStatus
from app.schemas.dashboard import DashboardResponse, CostSummary, MonthlyPerformance
from datetime import datetime, timedelta
from collections import defaultdict


def get_dashboard_data(
    db: Session,
    owner_id: str,
    period: str = "all",
) -> DashboardResponse:
    """
    Calcula todas as métricas do dashboard para o usuário autenticado.

    Períodos disponíveis:
    - all: todos os dados
    - month: mês atual
    - week: semana atual
    - today: hoje
    """

    # Busca todas as planilhas ativas do usuário
    sheets_query = db.query(Sheet).filter(
        Sheet.owner_id == owner_id,
        Sheet.is_deleted == False,
    )

    # Aplica filtro de período
    now = datetime.utcnow()

    if period == "today":
        sheets_query = sheets_query.filter(
            extract("day", Sheet.created_at) == now.day,
            extract("month", Sheet.created_at) == now.month,
            extract("year", Sheet.created_at) == now.year,
        )
    elif period == "week":
        # Filtra pela semana atual (últimos 7 dias)
        week_start = now - timedelta(days=7)
        sheets_query = sheets_query.filter(Sheet.created_at >= week_start)
    elif period == "month":
        sheets_query = sheets_query.filter(
            extract("month", Sheet.created_at) == now.month,
            extract("year", Sheet.created_at) == now.year,
        )

    sheets = sheets_query.all()

    # ─── TOTAIS FINANCEIROS ───────────────────────────────────

    total_deposited = 0.0
    total_received = 0.0
    total_chest = 0.0
    total_salary = 0.0
    total_operations = 0

    cost_proxy = 0.0
    cost_sms = 0.0
    cost_bot = 0.0
    cost_fintech = 0.0

    # Dados agrupados por mês para o gráfico
    monthly_data: dict = defaultdict(lambda: {
        "deposited": 0.0,
        "received": 0.0,
        "result": 0.0,
    })

    for sheet in sheets:
        # Acumula custos e salário de cada planilha
        cost_proxy += float(sheet.cost_proxy)
        cost_sms += float(sheet.cost_sms)
        cost_bot += float(sheet.cost_bot)
        cost_fintech += float(sheet.cost_fintech)
        total_salary += float(sheet.salary)

        # Chave do mês no formato "YYYY-MM"
        month_key = sheet.created_at.strftime("%Y-%m")

        for line in sheet.lines:
            # Conta apenas linhas que têm algum valor preenchido
            if line.deposit > 0 or line.withdrawal > 0 or line.chest > 0:
                total_operations += 1

            total_deposited += float(line.deposit)
            total_received += float(line.withdrawal)
            total_chest += float(line.chest)

            # Acumula dados mensais para o gráfico
            monthly_data[month_key]["deposited"] += float(line.deposit)
            monthly_data[month_key]["received"] += float(line.withdrawal)

    total_costs = cost_proxy + cost_sms + cost_bot + cost_fintech

    # Resultado final: recebido - depositado + baú + salário - custos
    final_result = total_received - total_deposited + total_chest + total_salary - total_costs

    # Calcula o resultado por mês para o gráfico
    for month_key in monthly_data:
        monthly_data[month_key]["result"] = (
            monthly_data[month_key]["received"] - monthly_data[month_key]["deposited"]
        )

    # Ordena os meses cronologicamente
    monthly_performance = [
        MonthlyPerformance(
            month=month,
            deposited=data["deposited"],
            received=data["received"],
            result=data["result"],
        )
        for month, data in sorted(monthly_data.items())
    ]

    return DashboardResponse(
        total_deposited=total_deposited,
        total_received=total_received,
        total_chest=total_chest,
        final_result=final_result,
        costs=CostSummary(
            proxy=cost_proxy,
            sms=cost_sms,
            bot=cost_bot,
            fintech=cost_fintech,
            total=total_costs,
        ),
        total_sheets=len(sheets),
        total_operations=total_operations,
        monthly_performance=monthly_performance,
    )