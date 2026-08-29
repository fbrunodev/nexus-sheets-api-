import pytest
from unittest.mock import MagicMock, patch
from app.models.sheet import Sheet, SheetLine
from app.services.sheet import (
    create_new_sheet, update_existing_sheet, add_lines, update_line,
    finish_sheet, remove_line, clear_all_lines, calculate_period_filter, delete_sheet,
)
from app.schemas.sheet import SheetCreate, SheetUpdate, SheetLineUpdate, SheetStatus
from app.exceptions.sheet_exceptions import (
    SheetLineNotFoundException, SheetAlreadyFinishedException, SheetNotFoundException,
)
from datetime import datetime, timedelta


class SheetRepositoryFake:
    def __init__(self):
        self.sheets = {}

    def get_sheet_by_id(self, sheet_id: str, owner_id: str) -> Sheet | None:
        sheet = self.sheets.get(sheet_id)
        if sheet and sheet.owner_id == owner_id:
            return sheet
        return None

    def create_sheet(self, sheet: Sheet) -> Sheet:
        self.sheets[sheet.id] = sheet
        return sheet

    def update_sheet(self, sheet: Sheet) -> Sheet:
        self.sheets[sheet.id] = sheet
        return sheet

    def soft_delete_sheet(self, sheet: Sheet) -> Sheet:
        sheet.is_deleted = True
        sheet.updated_at = datetime.utcnow()
        self.sheets[sheet.id] = sheet
        return sheet


class SheetLineRepositoryFake:
    def __init__(self):
        self.lines = {}

    def get_line_by_id(self, line_id: str, sheet_id: str) -> SheetLine | None:
        line = self.lines.get(line_id)
        if line and line.sheet_id == sheet_id:
            return line
        return None

    def bulk_create_lines(self, lines: list[SheetLine]) -> list[SheetLine]:
        for line in lines:
            self.lines[line.id] = line
        return lines

    def update_sheet_line(self, line: SheetLine) -> SheetLine:
        # result = withdrawal + chest + bonus - deposit
        line.result = float(line.withdrawal) - float(line.deposit) + float(line.chest) + float(line.bonus)
        self.lines[line.id] = line
        return line

    def delete_line(self, line: SheetLine) -> SheetLine:
        self.lines.pop(line.id, None)
        return line


def test_create_new_sheet_without_lines():
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    data = SheetCreate(
        name="Test Sheet",
        owner_id="owner123",
        platform_id=None,
        status="NEW",
        lines=[],
    )

    result = create_new_sheet(
        sheet_repo=sheet_repo,
        line_repo=line_repo,
        db=db_mock,
        data=data,
        owner_id="owner123",
    )

    assert result.name == "Test Sheet"
    assert result.owner_id == "owner123"


def test_update_existing_sheet():
    sheet_repo = SheetRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Old Name", owner_id="owner123")
    sheet_repo.create_sheet(existing)

    data = SheetUpdate(name="Test Sheet", owner_id="owner123")

    result = update_existing_sheet(
        sheet_repo=sheet_repo,
        db=db_mock,
        sheet_id="sheet123",
        data=data,
        owner_id="owner123",
    )

    assert result.name == "Test Sheet"
    assert result.owner_id == "owner123"


def test_finish_sheet():
    sheet_repo = SheetRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="test sheet", owner_id="owner123", salary=5, status=SheetStatus.IN_PROGRESS)
    existing.lines = [
        SheetLine(id="line1", sheet_id="sheet123", withdrawal=100, deposit=50, chest=10, bonus=20, result=0)
    ]
    sheet_repo.create_sheet(existing)

    with patch("app.services.sheet.send_push_to_user") as mock_push:
        result = finish_sheet(sheet_repo, db_mock, "sheet123", "owner123")

    assert result.status == SheetStatus.FINISHED
    mock_push.assert_called()


def test_soft_delete_sheet():
    sheet_repo = SheetRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Old Name", owner_id="owner123")
    sheet_repo.create_sheet(existing)

    delete_sheet(sheet_repo=sheet_repo, db=db_mock, sheet_id="sheet123", owner_id="owner123")

    deleted = sheet_repo.get_sheet_by_id("sheet123", "owner123")
    assert deleted.is_deleted is True


def test_calculate_period_filter_today():
    assert len(calculate_period_filter("today")) == 1


def test_calculate_period_filter_week():
    assert len(calculate_period_filter("week")) == 1


def test_calculate_period_filter_month():
    assert len(calculate_period_filter("month")) == 1


def test_calculate_period_filter_invalid():
    assert calculate_period_filter("anything") == []


def test_calculate_period_filter_none():
    assert calculate_period_filter(None) == []


# --- Sheet Lines -------------------------------------------------------------

def test_add_sheet_lines():
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Test Sheet", owner_id="owner123")
    existing.lines = [
        SheetLine(id="line1", sheet_id="sheet123", line_number=1, deposit=0, withdrawal=0, chest=0, result=0)
    ]
    sheet_repo.create_sheet(existing)

    result = add_lines(
        line_repo=line_repo,
        sheet_repo=sheet_repo,
        db=db_mock,
        sheet_id="sheet123",
        owner_id="owner123",
        quantity=2,
    )

    assert result.id == "sheet123"
    assert len(line_repo.lines) == 2


def test_update_sheet_line():
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Test Sheet", owner_id="owner123")
    existing.lines = [
        SheetLine(id="line1", sheet_id="sheet123", line_number=1, deposit=0, withdrawal=0, chest=0,bonus=0 ,result=0)
    ]
    sheet_repo.create_sheet(existing)
    line_repo.bulk_create_lines(existing.lines)

    data = SheetLineUpdate(deposit=100, withdrawal=120)

    result = update_line(
        sheet_repo=sheet_repo,
        line_repo=line_repo,
        db=db_mock,
        sheet_id="sheet123",
        line_id="line1",
        data=data,
        owner_id="owner123",
    )

    assert result.id == "line1"
    assert result.deposit == 100
    assert result.withdrawal == 120


def test_delete_line():
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Test Sheet", owner_id="owner123")
    line = SheetLine(id="line1", sheet_id="sheet123", line_number=1, deposit=100, withdrawal=50, chest=20, result=70)
    existing.lines = [line]
    sheet_repo.create_sheet(existing)
    line_repo.bulk_create_lines(existing.lines)

    result = remove_line(
        sheet_repo=sheet_repo,
        line_repo=line_repo,
        db=db_mock,
        sheet_id="sheet123",
        line_id="line1",
        owner_id="owner123",
    )

    assert result.id == "sheet123"
    assert line_repo.get_line_by_id("line1", "sheet123") is None


def test_clear_all_lines():
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Test Sheet", owner_id="owner123")
    line = SheetLine(id="line1", sheet_id="sheet123", line_number=1, deposit=100, withdrawal=50, chest=20, bonus=0, result=70)
    existing.lines = [line]
    sheet_repo.create_sheet(existing)
    line_repo.bulk_create_lines(existing.lines)

    result = clear_all_lines(
        sheet_repo=sheet_repo,
        line_repo=line_repo,
        db=db_mock,
        sheet_id="sheet123",
        owner_id="owner123",
    )

    assert result.id == "sheet123"
    updated_line = line_repo.get_line_by_id("line1", "sheet123")
    assert updated_line.deposit == 0
    assert updated_line.withdrawal == 0
    assert updated_line.chest == 0
    assert updated_line.result == 0


# --- Exception cases ---------------------------------------------------------

@pytest.mark.parametrize("call", [
    lambda sr, lr, db: update_existing_sheet(sr, db, "missing", SheetUpdate(name="x"), "owner123"),
    lambda sr, lr, db: finish_sheet(sr, db, "missing", "owner123"),
    lambda sr, lr, db: add_lines(lr, sr, db, "missing", "owner123", 2),
    lambda sr, lr, db: remove_line(sr, lr, db, "missing", "line1", "owner123"),
])
def test_raises_sheet_not_found(call):
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    with pytest.raises(SheetNotFoundException):
        call(sheet_repo, line_repo, db_mock)

def test_sheet_edit_line__of_an_already_finished_sheet():
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Test Sheet",status=SheetStatus.FINISHED, owner_id="owner123")
    sheet_repo.create_sheet(existing)

    with pytest.raises(SheetAlreadyFinishedException):
        update_line(
            sheet_repo=sheet_repo,
            line_repo=line_repo,
            db=db_mock,
            sheet_id="sheet123",
            line_id="nonexistent",
            data=SheetLineUpdate(deposit=100, withdrawal=120),
            owner_id="owner123",
        )

def test_remove_line_not_found():
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Test Sheet", owner_id="owner123")
    sheet_repo.create_sheet(existing)

    with pytest.raises(SheetLineNotFoundException):
        remove_line(
            sheet_repo=sheet_repo,
            line_repo=line_repo,
            db=db_mock,
            sheet_id="sheet123",
            line_id="nonexistent",
            owner_id="owner123",
        )


def test_update_line_not_found():
    sheet_repo = SheetRepositoryFake()
    line_repo = SheetLineRepositoryFake()
    db_mock = MagicMock()

    existing = Sheet(id="sheet123", name="Test Sheet", owner_id="owner123")
    sheet_repo.create_sheet(existing)

    with pytest.raises(SheetLineNotFoundException):
        update_line(
            sheet_repo=sheet_repo,
            line_repo=line_repo,
            db=db_mock,
            sheet_id="sheet123",
            line_id="nonexistent",
            data=SheetLineUpdate(deposit=100, withdrawal=120),
            owner_id="owner123",
        )
