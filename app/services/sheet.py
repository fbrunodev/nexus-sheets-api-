from sqlalchemy import func, case
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.sheet import Sheet, SheetLine, SheetStatus, CooperationType
from app.schemas.sheet import SheetCreate, SheetUpdate, SheetLineUpdate
from app.services.cost import get_total_costs
from app.services.push import send_push_to_user
from app.models.user import User, UserRole
from app.exceptions.sheet_exceptions import (
    SheetAlreadyFinishedException,
    SheetNotFoundException,
    SheetLineNotFoundException,
)
from app.repositories.sheet import SheetRepository, SheetLineRepository
import uuid
import logging

logger = logging.getLogger(__name__)


def calculate_period_filter(period: str | None) -> list:
    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return [Sheet.created_at >= start]
    if period == "week":
        return [Sheet.created_at >= now - timedelta(days=7)]
    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return [Sheet.created_at >= start]
    return []


def _recalculate_status(sheet: Sheet) -> None:
    # FINISHED is a terminal state set manually — never overridden by auto-recalculation.
    if sheet.status == SheetStatus.FINISHED:
        return

    has_data = any(
        line.deposit > 0 or line.withdrawal > 0 or line.chest > 0 or line.bonus > 0
        for line in sheet.lines
    )
    sheet.status = SheetStatus.IN_PROGRESS if has_data else SheetStatus.NOT_STARTED


# --- Sheet -------------------------------------------------------------------

def list_sheets(
    sheet_repo: SheetRepository, owner_id: str, limit: int = 10, offset: int = 0,
    status: str | None = None, search: str | None = None, period: str | None = None,
) -> list[Sheet]:
    period_filter = calculate_period_filter(period)
    return sheet_repo.get_sheets_by_owner(owner_id, limit, offset, status, search, period_filter)


def count_sheets(
    sheet_repo: SheetRepository, owner_id: str,
    status: str | None = None, search: str | None = None, period: str | None = None,
) -> int:
    period_filter = calculate_period_filter(period)
    return sheet_repo.count_sheets_by_owner(owner_id, status, search, period_filter)


def get_sheet(sheet_repo: SheetRepository, db: Session, sheet_id: str, owner_id: str) -> Sheet:
    """Fetch a sheet for viewing. Grants read access to the sheet's direct owner
    and to the supervisor/admin who owns the operator that created it."""
    sheet = sheet_repo.get_sheet_by_id(sheet_id, owner_id)

    if not sheet:
        # Second pass: check if the requester is a supervisor of the sheet's owner.
        sheet = db.query(Sheet).filter(Sheet.id == sheet_id, Sheet.is_deleted == False).first()
        if sheet:
            sheet_owner = db.query(User).filter(User.id == sheet.owner_id).first()
            if not sheet_owner or sheet_owner.owner_id != owner_id:
                sheet = None

    if not sheet:
        logger.warning("Sheet not found")
        raise SheetNotFoundException("Sheet not found.")

    return sheet


def get_sheet_for_edit(sheet_repo: SheetRepository, sheet_id: str, owner_id: str) -> Sheet:
    """Fetch a sheet for editing. Only the direct owner can modify — supervisors cannot."""
    sheet = sheet_repo.get_sheet_by_id(sheet_id, owner_id)
    if not sheet:
        logger.warning("Sheet not found")
        raise SheetNotFoundException("Sheet not found.")
    return sheet


def create_new_sheet(
    sheet_repo: SheetRepository, line_repo: SheetLineRepository,
    db: Session, data: SheetCreate, owner_id: str,
) -> Sheet:
    logger.info("Attempting to create sheet")

    new_sheet = Sheet(
        id=str(uuid.uuid4()),
        name=data.name,
        owner_id=owner_id,
        operator_id=data.operator_id,
        goal=data.goal,
        platform_id=data.platform_id,
        cooperation_type=data.cooperation_type or CooperationType.META,
    )

    created_sheet = sheet_repo.create_sheet(new_sheet)

    # If deposits were pasted in bulk, create one pre-filled line per value.
    # Otherwise create empty lines according to initial_lines.
    if data.deposits:
        lines = [
            SheetLine(
                id=str(uuid.uuid4()),
                sheet_id=created_sheet.id,
                line_number=i + 1,
                deposit=deposit,
                withdrawal=0,
                chest=0,
                result=-deposit,
            )
            for i, deposit in enumerate(data.deposits)
        ]
    else:
        lines = [
            SheetLine(
                id=str(uuid.uuid4()),
                sheet_id=created_sheet.id,
                line_number=i + 1,
                deposit=0,
                withdrawal=0,
                chest=0,
                result=0,
            )
            for i in range(data.initial_lines)
        ]

    line_repo.bulk_create_lines(lines)
    _recalculate_status(created_sheet)

    sheet_owner = db.query(User).filter(User.id == owner_id).first()
    if sheet_owner and sheet_owner.role == UserRole.OPERATOR and sheet_owner.owner_id:
        operator_name = sheet_owner.name or sheet_owner.email
        deposit_count = len(created_sheet.lines) if data.deposits else 0
        platform_name = created_sheet.name
        msg = (
            f"{operator_name} started {deposit_count} deposits on {platform_name}"
            if deposit_count > 0
            else f"{operator_name} created a sheet on {platform_name}"
        )
        send_push_to_user(db, sheet_owner.owner_id, "Nexus Sheets", msg)

    db.commit()
    db.refresh(created_sheet)
    logger.info(f"Sheet {new_sheet.id} created")
    return created_sheet


def update_existing_sheet(
    sheet_repo: SheetRepository, db: Session,
    sheet_id: str, data: SheetUpdate, owner_id: str,
) -> Sheet:
    logger.info("Attempting to update sheet")

    sheet = get_sheet_for_edit(sheet_repo, sheet_id, owner_id)

    if sheet.status == SheetStatus.FINISHED:
        logger.warning("Cannot edit a finished sheet")
        raise SheetAlreadyFinishedException("Cannot edit an already finished sheet.")

    if data.name is not None:
        sheet.name = data.name
    if data.operator_id is not None:
        sheet.operator_id = data.operator_id
    if data.salary is not None:
        sheet.salary = data.salary
    if data.goal is not None:
        sheet.goal = data.goal

    updated_sheet = sheet_repo.update_sheet(sheet)
    db.commit()
    db.refresh(sheet)
    logger.info(f"Sheet {updated_sheet.id} updated")
    return updated_sheet


def finish_sheet(sheet_repo: SheetRepository, db: Session, sheet_id: str, owner_id: str) -> Sheet:
    logger.info("Attempting to finish sheet")

    sheet = get_sheet_for_edit(sheet_repo, sheet_id, owner_id)

    if sheet.status == SheetStatus.FINISHED:
        logger.warning("Sheet is already finished")
        raise SheetAlreadyFinishedException("Cannot finish an already finished sheet.")

    sheet.status = SheetStatus.FINISHED
    updated = sheet_repo.update_sheet(sheet)
    db.commit()
    db.refresh(updated)
    logger.info(f"Sheet {updated.id} finished")

    total_withdrawal = sum(float(l.withdrawal) for l in sheet.lines)
    total_deposit = sum(float(l.deposit) for l in sheet.lines)
    total_chest = sum(float(l.chest) for l in sheet.lines)
    total_bonus = sum(float(l.bonus) for l in sheet.lines)
    result = total_withdrawal - total_deposit + total_chest + total_bonus + float(sheet.salary)
    result_str = f"+R$ {result:,.2f}" if result >= 0 else f"-R$ {abs(result):,.2f}"

    send_push_to_user(db, sheet.owner_id, "Nexus Sheets", f"{sheet.name} finished! Result: {result_str}")

    sheet_owner = db.query(User).filter(User.id == sheet.owner_id).first()
    if sheet_owner and sheet_owner.role == UserRole.OPERATOR and sheet_owner.owner_id:
        operator_name = sheet_owner.name or sheet_owner.email
        send_push_to_user(
            db, sheet_owner.owner_id, "Nexus Sheets",
            f"{operator_name} finished {sheet.name}! Result: {result_str}",
        )

    return sheet


def delete_sheet(sheet_repo: SheetRepository, db: Session, sheet_id: str, owner_id: str) -> None:
    logger.info("Attempting to delete sheet")
    sheet = get_sheet_for_edit(sheet_repo, sheet_id, owner_id)
    sheet_repo.soft_delete_sheet(sheet)
    db.commit()
    logger.info(f"Sheet {sheet_id} soft-deleted")


# --- Sheet Lines -------------------------------------------------------------

def update_line(
    sheet_repo: SheetRepository, line_repo: SheetLineRepository,
    db: Session, sheet_id: str, line_id: str, data: SheetLineUpdate, owner_id: str,
) -> SheetLine:
    logger.info("Attempting to update line")

    sheet = get_sheet_for_edit(sheet_repo, sheet_id, owner_id)

    if sheet.status == SheetStatus.FINISHED:
        logger.warning("Cannot edit a finished sheet")
        raise SheetAlreadyFinishedException("Cannot edit an already finished sheet.")

    line = line_repo.get_line_by_id(line_id, sheet_id)
    if not line:
        logger.warning("Line not found")
        raise SheetLineNotFoundException("Line not found.")

    if data.deposit is not None:
        line.deposit = data.deposit
    if data.withdrawal is not None:
        line.withdrawal = data.withdrawal
    if data.chest is not None:
        line.chest = data.chest
    if data.bonus is not None:
        line.bonus = data.bonus

    updated_line = line_repo.update_sheet_line(line)
    _recalculate_status(sheet)
    sheet_repo.update_sheet(sheet)
    db.commit()
    db.refresh(sheet)
    logger.info(f"Line {updated_line.id} updated")
    return updated_line


def add_lines(
    line_repo: SheetLineRepository, sheet_repo: SheetRepository,
    db: Session, sheet_id: str, owner_id: str, quantity: int,
) -> Sheet:
    logger.info("Attempting to add lines")

    sheet = get_sheet_for_edit(sheet_repo, sheet_id, owner_id)

    if sheet.status == SheetStatus.FINISHED:
        logger.warning("Cannot edit a finished sheet")
        raise SheetAlreadyFinishedException("Cannot edit an already finished sheet.")

    # Continue numbering from the current last line rather than from a fixed count,
    # so numbering stays consistent even after lines have been removed.
    last_number = max((line.line_number for line in sheet.lines), default=0)

    new_lines = [
        SheetLine(
            id=str(uuid.uuid4()),
            sheet_id=sheet_id,
            line_number=last_number + i + 1,
            deposit=0,
            withdrawal=0,
            chest=0,
            result=0,
        )
        for i in range(quantity)
    ]

    line_repo.bulk_create_lines(new_lines)
    db.commit()
    db.refresh(sheet)
    logger.info(f"Added {quantity} lines to sheet {sheet.id}")
    return sheet


def remove_line(
    sheet_repo: SheetRepository, line_repo: SheetLineRepository,
    db: Session, sheet_id: str, line_id: str, owner_id: str,
) -> Sheet:
    logger.info("Attempting to remove line")

    sheet = get_sheet_for_edit(sheet_repo, sheet_id, owner_id)

    if sheet.status == SheetStatus.FINISHED:
        logger.warning("Cannot edit a finished sheet")
        raise SheetAlreadyFinishedException("Cannot edit an already finished sheet.")

    line = line_repo.get_line_by_id(line_id, sheet_id)
    if not line:
        logger.warning("Line not found")
        raise SheetLineNotFoundException("Line not found.")

    line_repo.delete_line(line)
    _recalculate_status(sheet)
    sheet_repo.update_sheet(sheet)
    db.commit()
    db.refresh(sheet)
    logger.info(f"Line {line_id} removed from sheet {sheet.id}")
    return sheet


def clear_all_lines(
    sheet_repo: SheetRepository, line_repo: SheetLineRepository,
    db: Session, sheet_id: str, owner_id: str,
) -> Sheet:
    logger.info("Attempting to clear all lines")

    sheet = get_sheet_for_edit(sheet_repo, sheet_id, owner_id)

    if sheet.status == SheetStatus.FINISHED:
        logger.warning("Cannot edit a finished sheet")
        raise SheetAlreadyFinishedException("Cannot edit an already finished sheet.")

    for line in sheet.lines:
        line.deposit = 0
        line.withdrawal = 0
        line.chest = 0
        line.result = 0
        line.bonus = 0
        line_repo.update_sheet_line(line)

    _recalculate_status(sheet)
    sheet_repo.update_sheet(sheet)
    db.commit()
    db.refresh(sheet)
    logger.info(f"All lines cleared on sheet {sheet.id}")
    return sheet


# --- Stats -------------------------------------------------------------------

def calc_owner_stats(db: Session, owner_id: str, period: str) -> dict:
    # Subquery: aggregate line values per sheet so we can join them to the
    # sheets table without loading every line into Python memory.
    line_agg = (
        db.query(
            SheetLine.sheet_id,
            func.coalesce(func.sum(SheetLine.withdrawal), 0).label("total_withdrawal"),
            func.coalesce(func.sum(SheetLine.deposit), 0).label("total_deposit"),
            func.coalesce(func.sum(SheetLine.chest), 0).label("total_chest"),
            func.coalesce(func.sum(SheetLine.bonus), 0).label("total_bonus"),
        )
        .group_by(SheetLine.sheet_id)
        .subquery()
    )

    result = (
        db.query(
            func.count(Sheet.id).label("total"),
            func.sum(case((Sheet.status == SheetStatus.NOT_STARTED, 1), else_=0)).label("not_started"),
            func.sum(case((Sheet.status == SheetStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
            func.sum(case((Sheet.status == SheetStatus.FINISHED, 1), else_=0)).label("finished"),
            func.coalesce(
                func.sum(
                    func.coalesce(line_agg.c.total_withdrawal, 0)
                    - func.coalesce(line_agg.c.total_deposit, 0)
                    + func.coalesce(line_agg.c.total_chest, 0)
                    + func.coalesce(line_agg.c.total_bonus, 0)
                    + Sheet.salary
                ),
                0,
            ).label("grand_total"),
        )
        .outerjoin(line_agg, Sheet.id == line_agg.c.sheet_id)
        .filter(Sheet.owner_id == owner_id, Sheet.is_deleted == False)
        .filter(*calculate_period_filter(period))
        .one()
    )

    now = datetime.utcnow()
    if period == "all":
        total_costs = get_total_costs(db, owner_id, month=None, year=None)
    else:
        total_costs = get_total_costs(db, owner_id, month=now.month, year=now.year)

    grand_total = float(result.grand_total or 0) - total_costs

    return {
        "total": result.total or 0,
        "not_started": int(result.not_started or 0),
        "in_progress": int(result.in_progress or 0),
        "finished": int(result.finished or 0),
        "grand_total": grand_total,
    }


def get_sheets_stats(db: Session, owner_id: str, period: str = "all") -> dict:
    # Aggregate the owner's own sheets, then fold in each operator's totals.
    # This gives a consolidated view across the entire hierarchy.
    principal_stats = calc_owner_stats(db, owner_id, period)

    operator_ids = [
        u.id for u in db.query(User)
        .filter(User.owner_id == owner_id, User.role == UserRole.OPERATOR)
        .all()
    ]

    grand_total = principal_stats["grand_total"]
    for op_id in operator_ids:
        grand_total += calc_owner_stats(db, op_id, period)["grand_total"]

    principal_stats["grand_total"] = grand_total
    return principal_stats
