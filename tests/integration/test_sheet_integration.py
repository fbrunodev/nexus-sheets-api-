from conftest import db_session
from app.models.user import User
from app.models.sheet import Sheet, SheetLine, SheetStatus
from app.repositories.sheet import SheetRepository, SheetLineRepository
from app.services.sheet import calculate_period_filter, count_sheets, get_sheets_stats
from datetime import datetime, timedelta

def test_get_sheets_by_owner_filters_by_status(db_session):
    sheet_repo = SheetRepository(db_session)

    owner = User(id="owner123", email="owner@test.com", password_hash="fake_hash")
    db_session.add(owner)
    db_session.commit()

    sheet1 = Sheet(id="s1", name="Sheet 1", owner_id="owner123", status=SheetStatus.NOT_STARTED)
    sheet2 = Sheet(id="s2", name="Sheet 2", owner_id="owner123", status=SheetStatus.FINISHED)
    db_session.add_all([sheet1, sheet2])
    db_session.commit()

    result = sheet_repo.get_sheets_by_owner(owner_id="owner123", status="NOT_STARTED")

    assert len(result) == 1
    assert result[0].id == "s1"


def test_period_filter_applied_in_real_query(db_session):
   

    owner = User(id="owner123", email="owner@test.com", password_hash="fake_hash")
    db_session.add(owner)
    db_session.commit()

    recent = Sheet(id="s1", name="Recent", owner_id="owner123", created_at=datetime.utcnow())
    old = Sheet(
        id="s2", name="Old", owner_id="owner123",
        created_at=datetime.utcnow() - timedelta(days=60),
    )
    db_session.add_all([recent, old])
    db_session.commit()

    sheet_repo = SheetRepository(db_session)
    period_filter = calculate_period_filter("month")
    result = sheet_repo.get_sheets_by_owner(owner_id="owner123", period_filter=period_filter)

    assert len(result) == 1
    assert result[0].id == "s1"


def test_count_sheets_by_owner(db_session):
    owner = User(id="owner123", email="owner@test.com", password_hash="fake_hash")
    db_session.add(owner)
    db_session.commit()

    sheet1 = Sheet(id="s1", name="Sheet 1", owner_id="owner123", status=SheetStatus.NOT_STARTED)
    sheet2 = Sheet(id="s2", name="Sheet 2", owner_id="owner123", status=SheetStatus.FINISHED)
    sheet3 = Sheet(id="s3", name="Sheet 3", owner_id="owner123", status=SheetStatus.FINISHED)
    db_session.add_all([sheet1, sheet2, sheet3])
    db_session.commit()

    sheet_repo = SheetRepository(db_session)
    result = sheet_repo.count_sheets_by_owner(owner_id="owner123", status="FINISHED")

    assert result == 2


def test_get_sheet_stats(db_session):
    owner = User(id="owner123", email="owner@test.com", password_hash="fake_hash")
    db_session.add(owner)
    db_session.commit()

    sheet1 = Sheet(id="s1", name="Sheet 1", owner_id="owner123", status=SheetStatus.NOT_STARTED)
    sheet2 = Sheet(id="s2", name="Sheet 2", owner_id="owner123", status=SheetStatus.FINISHED)
    sheet3 = Sheet(id="s3", name="Sheet 3", owner_id="owner123", status=SheetStatus.FINISHED)
    db_session.add_all([sheet1, sheet2, sheet3])
    db_session.commit()

    sheet1.lines = [
        SheetLine(id="l1", sheet_id="s1", line_number=1, withdrawal=100, deposit=50, chest=0, bonus=0, result=0)
    ]
    db_session.add_all(sheet1.lines)
    db_session.commit()

    result = get_sheets_stats(db_session, owner_id="owner123", period="all")

    assert result["total"] == 3
    assert result["not_started"] == 1
    assert result["in_progress"] == 0
    assert result["finished"] == 2
    assert result["grand_total"] == 50.0
