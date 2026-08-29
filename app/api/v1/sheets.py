from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.sheet import Sheet
from app.schemas.sheet import (
    SheetCreate,
    SheetUpdate,
    SheetResponse,
    SheetLineUpdate,
    SheetLineResponse,
)
from app.repositories.sheet import SheetRepository, SheetLineRepository
from app.services.sheet import (
    list_sheets,
    get_sheet,
    create_new_sheet,
    update_existing_sheet,
    finish_sheet,
    delete_sheet,
    update_line,
    count_sheets,
    get_sheets_stats,
    add_lines,
    remove_line,
    clear_all_lines,
)
from app.exceptions.sheet_exceptions import (
    SheetAlreadyFinishedException,
    SheetNotFoundException,
    SheetLineNotFoundException,
)

router = APIRouter(prefix="/sheets", tags=["Sheets"])


@router.get("/")
def get_sheets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str = Query(None),
    search: str = Query(None),
    period: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    period_val = period if period in ("month", "week") else None
    items = list_sheets(sheet_repo, current_user.id, limit, offset, status or None, search or None, period_val)
    total = count_sheets(sheet_repo, current_user.id, status or None, search or None, period_val)

    return {
        "items": [SheetResponse.model_validate(s) for s in items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


@router.get("/stats")
def get_stats(
    period: str = Query(default="all", description="Period: all, month, week, today"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_sheets_stats(db, current_user.id, period)


@router.post("/", response_model=SheetResponse, status_code=201)
def create_sheet(
    data: SheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    line_repo = SheetLineRepository(db)
    return create_new_sheet(sheet_repo, line_repo, db, data, current_user.id)


@router.get("/operator-sheets")
def get_operator_sheets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns sheets from all operators linked to the authenticated user."""
    from app.models.user import UserRole

    # Raw queries used here intentionally — no repository abstraction for this
    # cross-entity read. Candidate for extraction if the query grows more complex.
    operators = db.query(User).filter(
        User.owner_id == current_user.id, User.role == UserRole.OPERADOR
    ).all()
    operator_ids = [op.id for op in operators]

    if not operator_ids:
        return {"items": [], "total": 0, "operators": []}

    sheets = db.query(Sheet).filter(
        Sheet.owner_id.in_(operator_ids),
        Sheet.is_deleted == False,
    ).order_by(Sheet.created_at.desc()).offset(offset).limit(limit).all()

    total = db.query(func.count(Sheet.id)).filter(
        Sheet.owner_id.in_(operator_ids),
        Sheet.is_deleted == False,
    ).scalar()

    operator_map = {op.id: (op.name or op.email) for op in operators}

    return {
        "items": [
            {"sheet": SheetResponse.model_validate(s), "operator_name": operator_map.get(s.owner_id, "?")}
            for s in sheets
        ],
        "total": total,
        "operators": [{"id": op.id, "name": op.name or op.email} for op in operators],
    }


@router.get("/{sheet_id}", response_model=SheetResponse)
def get_sheet_by_id(
    sheet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    try:
        return get_sheet(sheet_repo, db, sheet_id, current_user.id)
    except SheetNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{sheet_id}", response_model=SheetResponse)
def update_sheet(
    sheet_id: str,
    data: SheetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    try:
        return update_existing_sheet(sheet_repo, db, sheet_id, data, current_user.id)
    except SheetNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SheetAlreadyFinishedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{sheet_id}/finish", response_model=SheetResponse)
def finish_sheet_endpoint(
    sheet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    try:
        return finish_sheet(sheet_repo, db, sheet_id, current_user.id)
    except SheetNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SheetAlreadyFinishedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{sheet_id}", status_code=204)
def delete_sheet_endpoint(
    sheet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    try:
        delete_sheet(sheet_repo, db, sheet_id, current_user.id)
    except SheetNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{sheet_id}/lines/{line_id}", response_model=SheetLineResponse)
def update_line_endpoint(
    sheet_id: str,
    line_id: str,
    data: SheetLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    line_repo = SheetLineRepository(db)
    try:
        return update_line(sheet_repo, line_repo, db, sheet_id, line_id, data, current_user.id)
    except SheetNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SheetAlreadyFinishedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SheetLineNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{sheet_id}/lines", response_model=SheetResponse)
def add_lines_endpoint(
    sheet_id: str,
    quantity: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    line_repo = SheetLineRepository(db)
    try:
        return add_lines(line_repo, sheet_repo, db, sheet_id, current_user.id, quantity)
    except SheetNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SheetAlreadyFinishedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{sheet_id}/lines/{line_id}", response_model=SheetResponse)
def remove_line_endpoint(
    sheet_id: str,
    line_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    line_repo = SheetLineRepository(db)
    try:
        return remove_line(sheet_repo, line_repo, db, sheet_id, line_id, current_user.id)
    except SheetNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SheetAlreadyFinishedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SheetLineNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{sheet_id}/clear", response_model=SheetResponse)
def clear_lines_endpoint(
    sheet_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet_repo = SheetRepository(db)
    line_repo = SheetLineRepository(db)
    try:
        return clear_all_lines(sheet_repo, line_repo, db, sheet_id, current_user.id)
    except SheetNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SheetAlreadyFinishedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
