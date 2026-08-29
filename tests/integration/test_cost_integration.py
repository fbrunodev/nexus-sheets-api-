import pytest
from conftest import db_session
from app.models.user import User, UserRole
from app.models.cost import Cost, CostType
from app.schemas.cost import CostCreate, CostTypeCreate, CostResponse, CostTypeResponse
from app.services.cost import get_cost_stats, create_cost_type, delete_cost_type, delete_cost, add_cost_to_a_user
from datetime import datetime
from app.exceptions.cost_exceptions import CostAlreadyExistsException, CostNotFoundException, CostTypeNotFoundException


def test_cost_stats(db_session):
    owner = User(
        id="owner123",
        email="owner@test.com",
        password_hash="fake_hash",
        role=UserRole.ADMIN,
    )
    db_session.add(owner)
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

    result = get_cost_stats(db_session, owner_id="owner123", period="month")

    assert result == [{"name": "BOT", "value": 20}]



def test_create_cost_type_already_exists(db_session):
    
    owner = User(
        id="owner123",
        email="owner@test.com",
        password_hash="fake_hash",
        role=UserRole.ADMIN,
        )
    db_session.add(owner)
    db_session.commit()
    
    
    cost_type = CostType(
        id="cost_type123",
        name="Proxy",
        created_by="owner123",
        created_at=datetime.utcnow(),
    )
    db_session.add(cost_type)
    db_session.commit()
    
    
    data = CostTypeCreate(name ="Proxy")
    
    with pytest.raises(CostAlreadyExistsException):
        create_cost_type(db_session, data, admin_id="owner123")
    
    
def test_delete_cost_type_not_found(db_session):
 
    with pytest.raises(CostTypeNotFoundException):
        delete_cost_type(db_session, cost_type_id="cost_type123")
        
        
        
def test_add_cost_to_a_user_cost_type_not_found(db_session):
    owner = User(
        id="owner123",
        email="owner@test.com",
        password_hash="fake_hash",
        role=UserRole.ADMIN,
        )
    db_session.add(owner)
    db_session.commit()
    
    data = CostCreate(
        id="cost2",
        cost_type_id="cost_type123",
        owner_id="owner123",
        value=10,
        month=8,
        year=2026,
        description="test",
        created_at=datetime.utcnow(),
    )
    
    with pytest.raises(CostTypeNotFoundException):
        add_cost_to_a_user(db_session, data=data, owner_id="owner123")
        
        
        
def test_delete_cost_not_found(db_session):
    
    with pytest.raises(CostNotFoundException):
        delete_cost(db_session, cost_id="cost123", owner_id="owner123")