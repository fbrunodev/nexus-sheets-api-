from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.models.sheet import Sheet
from app.schemas.monthly import MonthlyProfitEntry
from app.services.calculations import calc_sheet_result
from app.services.cost import get_total_costs
from app.services.sheet import get_operator_ids

BRT = ZoneInfo("America/Sao_Paulo")


def _iter_months(now_brt: datetime, months: int) -> list[tuple[int, int]]:
    """Return (year, month) tuples for the last `months` months, oldest first."""
    base_year = now_brt.year
    base_month = now_brt.month
    result = []
    for i in range(months - 1, -1, -1):
        total = base_year * 12 + (base_month - 1) - i
        result.append((total // 12, total % 12 + 1))
    return result


def _brt_month_start_as_naive_utc(year: int, month: int) -> datetime:
    """First instant of year/month in BRT, returned as naive UTC for DB comparison."""
    brt_start = datetime(year, month, 1, 0, 0, 0, tzinfo=BRT)
    return brt_start.astimezone(timezone.utc).replace(tzinfo=None)


def get_monthly_profit(
    db: Session, owner_id: str, months: int
) -> list[MonthlyProfitEntry]:
    now_brt = datetime.now(tz=timezone.utc).astimezone(BRT)
    month_range = _iter_months(now_brt, months)

    # Same visibility as grand_total: owner + all direct operators
    all_owner_ids = [owner_id] + get_operator_ids(db, owner_id)

    oldest_year, oldest_month = month_range[0]
    window_start_utc = _brt_month_start_as_naive_utc(oldest_year, oldest_month)

    sheets = (
        db.query(Sheet)
        .filter(
            Sheet.owner_id.in_(all_owner_ids),
            Sheet.is_deleted == False,
            Sheet.created_at >= window_start_utc,
        )
        .all()
    )

    # Group sheets by BRT month key
    bucket: dict[str, list[Sheet]] = {f"{y}-{m:02d}": [] for y, m in month_range}
    for sheet in sheets:
        brt_dt = sheet.created_at.replace(tzinfo=timezone.utc).astimezone(BRT)
        key = brt_dt.strftime("%Y-%m")
        if key in bucket:
            bucket[key].append(sheet)

    entries = []
    for year, month in month_range:
        key = f"{year}-{month:02d}"
        month_sheets = bucket[key]

        sheets_result = sum(calc_sheet_result(s) for s in month_sheets)
        costs = sum(
            get_total_costs(db, oid, month=month, year=year)
            for oid in all_owner_ids
        )
        entries.append(
            MonthlyProfitEntry(
                month=key,
                sheets_result=round(sheets_result, 2),
                costs=round(costs, 2),
                profit=round(sheets_result - costs, 2),
                sheets_count=len(month_sheets),
            )
        )

    return entries
