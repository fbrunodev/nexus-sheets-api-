from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.models.sheet import Sheet, SheetLine, SheetStatus
from app.schemas.dashboard import DashboardResponse, CostSummary, MonthlyPerformance
from datetime import datetime, timedelta
from collections import defaultdict
from app.services.cost import get_cost_stats

def get_dashboard_data(db: Session, owner_id: str, period: str = "all") -> DashboardResponse:
    sheets_query = db.query(Sheet).filter(
        Sheet.owner_id == owner_id,
        Sheet.is_deleted == False,
    )

    now = datetime.utcnow()

    if period == "today":
        sheets_query = sheets_query.filter(
            extract("day", Sheet.created_at) == now.day,
            extract("month", Sheet.created_at) == now.month,
            extract("year", Sheet.created_at) == now.year,
        )
    elif period == "week":
        sheets_query = sheets_query.filter(Sheet.created_at >= now - timedelta(days=7))
    elif period == "month":
        sheets_query = sheets_query.filter(
            extract("month", Sheet.created_at) == now.month,
            extract("year", Sheet.created_at) == now.year,
        )

    sheets = sheets_query.all()

    total_deposited = 0.0
    total_received = 0.0
    total_chest = 0.0
    total_salary = 0.0
    total_bonus = 0.0
    total_operations = 0



    # "YYYY-MM" → aggregated financials for that month (used by the chart).
    monthly_data: dict = defaultdict(lambda: {"deposited": 0.0, "received": 0.0, "result": 0.0})

    for sheet in sheets:
        total_salary += float(sheet.salary)
        month_key = sheet.created_at.strftime("%Y-%m")

        for line in sheet.lines:
            if line.deposit > 0 or line.withdrawal > 0 or line.chest > 0:
                total_operations += 1

            total_deposited += float(line.deposit)
            total_received += float(line.withdrawal)
            total_chest += float(line.chest)
            total_bonus += float(line.bonus)

            monthly_data[month_key]["deposited"] += float(line.deposit)
            monthly_data[month_key]["received"] += float(line.withdrawal)


    
    cost_results = get_cost_stats(db, owner_id, period)
    cost_map = {item["name"]: item["value"] for item in cost_results}
    cost_proxy = cost_map.get("PROXY",0.0)
    cost_sms = cost_map.get("SMS", 0.0)
    cost_bot = cost_map.get("BOT",0.0)
    cost_fintech = cost_map.get("FINTECH", 0.0)
    total_costs = sum(cost_map.values())
    
    final_result = total_received - total_deposited + total_chest + total_bonus +  total_salary - total_costs

    for month_key in monthly_data:
        monthly_data[month_key]["result"] = (
            monthly_data[month_key]["received"] - monthly_data[month_key]["deposited"]
        )

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

