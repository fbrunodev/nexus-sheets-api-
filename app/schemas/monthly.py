from pydantic import BaseModel


class MonthlyProfitEntry(BaseModel):
    month: str          # "YYYY-MM"
    sheets_result: float
    costs: float
    profit: float
    sheets_count: int
