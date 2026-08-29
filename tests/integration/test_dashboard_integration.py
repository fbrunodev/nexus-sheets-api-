import pytest
from conftest import db_session
from app.models import (
    User,
    Cost,
    CostType,
)
from app.models.sheet import Sheet, SheetLine, SheetStatus
from app.services.dashboard import get_dashboard_data
from datetime import datetime

def test_dashboard_data(db_session):


    user = User(
        id="owner123",
        email = "user@gmail.com",
        password_hash = "fake_hash"
    )
    db_session.add(user)
    db_session.commit()
    
    sheet1 = Sheet(id="s1", name="Sheet 1", owner_id="owner123", status=SheetStatus.NOT_STARTED)
    db_session.add(sheet1)
    sheet1.lines = [
            SheetLine(id="l1", sheet_id="s1", line_number=1, withdrawal=200, deposit=100, chest=0, bonus=0, result=0)
    ]
    db_session.add_all(sheet1.lines)
    db_session.commit()
    
    
    cost_type = CostType(
            id="cost_type123",
            name="BOT",
            created_by="owner123",
            created_at=datetime.utcnow(),
        )
    db_session.add(cost_type)
    db_session.commit()
    
    cost_type.costs = [
            Cost(
                id="cost1",
                cost_type_id="cost_type123",
                owner_id="owner123",
                value=10,
                month=8,
                year=2026,
                description="test",
                created_at=datetime.utcnow(),
            ),
            Cost(
                id="cost2",
                cost_type_id="cost_type123",
                owner_id="owner123",
                value=10,
                month=8,
                year=2026,
                description="test",
                created_at=datetime.utcnow(),
            ),
        ]
    db_session.add_all(cost_type.costs)
    db_session.commit()
    
    
    result = get_dashboard_data(db_session, owner_id="owner123")
    
    assert result.costs.bot == 20
    assert result.final_result == 80
    
    
    
def test_dashboard_data_com_bonus(db_session):
    user = User(id="owner123", email="user@gmail.com", password_hash="fake_hash")
    db_session.add(user)
    db_session.commit()

    sheet1 = Sheet(id="s1", name="Sheet 1", owner_id="owner123", status=SheetStatus.NOT_STARTED)
    db_session.add(sheet1)
    sheet1.lines = [
        SheetLine(id="l1", sheet_id="s1", line_number=1, withdrawal=200, deposit=100, chest=0, bonus=30, result=0)
    ]
    db_session.add_all(sheet1.lines)
    db_session.commit()

    result = get_dashboard_data(db_session, owner_id="owner123")

    # 200 - 100 + 0 + 30 (bonus) + 0 (salary) - 0 (sem custos) = 130
    assert result.final_result == 130