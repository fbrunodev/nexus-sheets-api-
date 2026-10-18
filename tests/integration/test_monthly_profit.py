from conftest import db_session
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.models.user import User, UserRole
from app.models.sheet import Sheet, SheetLine, SheetStatus, CooperationType
from app.models.cost import Cost, CostType
from app.services.monthly import get_monthly_profit, _iter_months, _brt_month_start_as_naive_utc
from app.services.sheet import get_sheets_stats

BRT = ZoneInfo("America/Sao_Paulo")


# --- helpers -----------------------------------------------------------------

def _user(id, email, role=UserRole.ADMIN, owner_id=None):
    return User(id=id, email=email, password_hash="x", role=role, owner_id=owner_id)


def _sheet(id, owner_id, lines=None, salary=0.0,
           cooperation_type=CooperationType.META, created_at=None):
    now = datetime.utcnow()
    s = Sheet(
        id=id, name=f"Sheet {id}", owner_id=owner_id,
        salary=salary, cooperation_type=cooperation_type,
        status=SheetStatus.NOT_STARTED,
        created_at=created_at or now,
    )
    s.lines = [
        SheetLine(
            id=f"{id}-l{i}", sheet_id=id, line_number=i + 1,
            deposit=l.get("deposit", 0), withdrawal=l.get("withdrawal", 0),
            chest=l.get("chest", 0), bonus=l.get("bonus", 0), result=0,
        )
        for i, l in enumerate(lines or [])
    ]
    return s


# --- unit: timezone helpers --------------------------------------------------

def test_iter_months_returns_oldest_first():
    now = datetime(2026, 3, 15, tzinfo=BRT)
    result = _iter_months(now, 3)
    assert result == [(2026, 1), (2026, 2), (2026, 3)]


def test_iter_months_crosses_year_boundary():
    now = datetime(2026, 1, 10, tzinfo=BRT)
    result = _iter_months(now, 3)
    assert result == [(2025, 11), (2025, 12), (2026, 1)]


def test_brt_month_start_is_before_utc_midnight():
    # BRT = UTC-3, so Oct 1 00:00 BRT = Oct 1 03:00 UTC (naive)
    utc = _brt_month_start_as_naive_utc(2026, 10)
    assert utc == datetime(2026, 10, 1, 3, 0, 0)


def test_brt_virada_de_mes_cai_em_outubro():
    """Sheet created at 22:30 BRT Oct 31 (= 01:30 UTC Nov 1) must be classified as October."""
    brt_oct31 = datetime(2026, 10, 31, 22, 30, 0, tzinfo=BRT)
    utc_naive = brt_oct31.astimezone(timezone.utc).replace(tzinfo=None)

    # The UTC naive value should be Nov 1
    assert utc_naive.month == 11

    # Converting back to BRT must give October
    back = utc_naive.replace(tzinfo=timezone.utc).astimezone(BRT)
    assert back.month == 10
    assert back.day == 31


# --- integration -------------------------------------------------------------

def test_basic_profit(db_session):
    now_utc = datetime.utcnow()
    owner = _user("o1", "owner@test.com")
    db_session.add(owner)
    db_session.flush()

    ct = CostType(id="ct1", name="Tipo", created_by="o1")
    db_session.add(ct)
    db_session.flush()

    sheet = _sheet("s1", "o1", lines=[{"withdrawal": 300, "deposit": 100}], salary=200.0)
    db_session.add(sheet)
    db_session.add_all(sheet.lines)
    db_session.flush()

    cost = Cost(id="c1", cost_type_id="ct1", owner_id="o1", value=50.0,
                month=now_utc.month, year=now_utc.year)
    db_session.add(cost)
    db_session.commit()

    results = get_monthly_profit(db_session, "o1", months=1)
    assert len(results) == 1
    entry = results[0]
    # lines: 300-100=200; salary: 200; total: 400; costs: 50; profit: 350
    assert entry.sheets_result == 400.0
    assert entry.costs == 50.0
    assert entry.profit == 350.0
    assert entry.sheets_count == 1


def test_bau_salary_excluded(db_session):
    owner = _user("o1", "owner@test.com")
    db_session.add(owner)
    db_session.flush()
    sheet = _sheet("s1", "o1", lines=[{"withdrawal": 100, "deposit": 50}],
                   salary=500.0, cooperation_type=CooperationType.BAU)
    db_session.add(sheet)
    db_session.add_all(sheet.lines)
    db_session.commit()

    results = get_monthly_profit(db_session, "o1", months=1)
    # BAU: salary ignored; result = 100-50 = 50
    assert results[0].sheets_result == 50.0


def test_operator_sheets_included(db_session):
    owner = _user("o1", "owner@test.com", role=UserRole.SUPERVISOR)
    db_session.add(owner)
    db_session.flush()
    operator = _user("op1", "op@test.com", role=UserRole.OPERADOR, owner_id="o1")
    db_session.add(operator)
    db_session.flush()

    s_owner = _sheet("s1", "o1", lines=[{"withdrawal": 100, "deposit": 40}])
    s_op = _sheet("s2", "op1", lines=[{"withdrawal": 200, "deposit": 80}])
    for s in (s_owner, s_op):
        db_session.add(s)
        db_session.add_all(s.lines)
    db_session.commit()

    entry = get_monthly_profit(db_session, "o1", months=1)[0]
    # owner: 60; operator: 120; total: 180
    assert entry.sheets_result == 180.0
    assert entry.sheets_count == 2


def test_operator_costs_included(db_session):
    owner = _user("o1", "owner@test.com", role=UserRole.SUPERVISOR)
    db_session.add(owner)
    db_session.flush()
    operator = _user("op1", "op@test.com", role=UserRole.OPERADOR, owner_id="o1")
    db_session.add(operator)
    db_session.flush()

    ct = CostType(id="ct1", name="Tipo", created_by="o1")
    db_session.add(ct)
    db_session.flush()

    now = datetime.utcnow()
    cost_owner = Cost(id="c1", cost_type_id="ct1", owner_id="o1",
                      value=100.0, month=now.month, year=now.year)
    cost_op = Cost(id="c2", cost_type_id="ct1", owner_id="op1",
                   value=50.0, month=now.month, year=now.year)
    db_session.add_all([cost_owner, cost_op])
    db_session.commit()

    entry = get_monthly_profit(db_session, "o1", months=1)[0]
    assert entry.costs == 150.0


def test_operator_sees_only_own_sheets(db_session):
    """Operator calling monthly only sees their own sheets, not the owner's."""
    owner = _user("o1", "owner@test.com", role=UserRole.SUPERVISOR)
    db_session.add(owner)
    db_session.flush()
    operator = _user("op1", "op@test.com", role=UserRole.OPERADOR, owner_id="o1")
    db_session.add(operator)
    db_session.flush()

    s_owner = _sheet("s1", "o1", lines=[{"withdrawal": 100}])
    s_op = _sheet("s2", "op1", lines=[{"withdrawal": 200}])
    for s in (s_owner, s_op):
        db_session.add(s)
        db_session.add_all(s.lines)
    db_session.commit()

    entry = get_monthly_profit(db_session, "op1", months=1)[0]
    assert entry.sheets_count == 1
    assert entry.sheets_result == 200.0


def test_empty_months_return_zeros(db_session):
    owner = _user("o1", "owner@test.com")
    db_session.add(owner)
    db_session.commit()

    results = get_monthly_profit(db_session, "o1", months=3)
    assert len(results) == 3
    for entry in results:
        assert entry.sheets_result == 0.0
        assert entry.costs == 0.0
        assert entry.profit == 0.0
        assert entry.sheets_count == 0


def test_results_ordered_oldest_to_newest(db_session):
    owner = _user("o1", "owner@test.com")
    db_session.add(owner)
    db_session.commit()

    results = get_monthly_profit(db_session, "o1", months=6)
    assert len(results) == 6
    months = [e.month for e in results]
    assert months == sorted(months)


def test_profit_equals_grand_total(db_session):
    """sum(profit) over N months == grand_total when all data is within the window."""
    now_utc = datetime.utcnow()
    owner = _user("o1", "owner@test.com")
    db_session.add(owner)
    db_session.flush()

    ct = CostType(id="ct1", name="Tipo", created_by="o1")
    db_session.add(ct)
    db_session.flush()

    sheet = _sheet("s1", "o1", lines=[{"withdrawal": 500, "deposit": 200}], salary=100.0)
    db_session.add(sheet)
    db_session.add_all(sheet.lines)
    db_session.flush()

    cost = Cost(id="c1", cost_type_id="ct1", owner_id="o1", value=80.0,
                month=now_utc.month, year=now_utc.year)
    db_session.add(cost)
    db_session.commit()

    monthly = get_monthly_profit(db_session, "o1", months=6)
    total_profit = round(sum(e.profit for e in monthly), 2)

    stats = get_sheets_stats(db_session, "o1", period="all")
    assert total_profit == round(stats["grand_total"], 2)
