
from fastapi.testclient import TestClient
from main import app 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import get_db, Base
from app.models.user import User, PlanType 
from app.models.platform import Platform
from app.models.sheet import Sheet, CooperationType, SheetStatus
from app.core.security import hash_password
from datetime import timedelta
from app.core.security import create_access_token

TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/nexus_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally: 
        db.close()
        
        
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_login_e2e_success():
    db = TestingSessionLocal()
    Base.metadata.create_all(engine)
    try: 
        user = User(
            id="user123",
            email = "user@gmail.com",
            password_hash = hash_password("senha123"),
            is_active = True,
            plan_type = PlanType.LIFETIME,
        )
        db.add(user)
        db.commit()
        
        
        response = client.post("/api/v1/auth/login",json={
            "email": "user@gmail.com",
            "password": "senha123"
        })
        
        assert response.status_code == 200
        assert "access_token" in response.json()
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        
        
def test_create_sheet_with_user_authenticated():
    db = TestingSessionLocal()
    Base.metadata.create_all(engine)
    
    try:
        user = User(
            id="user123",
            email = "user@gmail.com",
            password_hash = hash_password("senha123"),
            is_active = True,
            plan_type = PlanType.LIFETIME,
        )
        db.add(user)
        
        
        platform = Platform(
            id="platform123",
            name ="TestePlatform"
        )
        db.add(platform)
        db.commit()
        
        login_response = client.post("api/v1/auth/login", json={
            "email" : "user@gmail.com",
            "password": "senha123"
        }) 
        assert login_response.status_code == 200
        token= login_response.json()["access_token"]
      
        response = client.post("api/v1/sheets/",
            headers={"Authorization": f"Bearer {token}"}, 
            json={
                "name": "testesheet",
                "initial_lines": 15,
                "goal": 20,
                "platform_id": "platform123",
                "cooperation_type": "META" 
            })
        
        
        
        assert response.status_code == 201, f"Esperava 201, recebeu {response.status_code}: {response.json()}"
        assert response.json()["name"] =="testesheet"
        
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        
        
        
def test_trying_to_accesss_and_edit_operator_sheet():
    db = TestingSessionLocal()
    Base.metadata.create_all(engine)
    
    try:
        
        user = User(
            id="user123",
            email = "user@gmail.com",
            password_hash = hash_password("senha123"),
            is_active = True,
            plan_type = PlanType.LIFETIME,
        )
        db.add(user)
        
        operator = User(
            id="operator123",
            email ="operator@gmail.com",
            password_hash = hash_password("senha123"),
            is_active =True,
            plan_type = PlanType.LIFETIME,
            owner_id = "user123"
        )
        db.add(operator)
        db.commit()
        
        platform = Platform(
            id="platform123",
            name ="TestePlatform"
        )
        db.add(platform)
        
        sheet = Sheet(
            id="sheet123",
            name = "TestePlatform",
            goal = 20,
            cooperation_type = CooperationType.META,
            owner_id = "operator123",
            status = SheetStatus.NOT_STARTED,
            platform_id = "platform123"
            
        )
        db.add(sheet)
        db.commit()
        
        # Trying to update a sheet from a user that isn't its owner
        login_response = client.post("api/v1/auth/login", json={
            "email": "user@gmail.com",
            "password": "senha123"
        })
        token = login_response.json()["access_token"]
        
        response = client.patch("api/v1/sheets/sheet123", 
            headers={"Authorization": f"Bearer {token}"} ,                      
            json={
                "salary" : 300.00
            })
        assert response.status_code == 404 , f"Esperado 404 retornou {response.status_code}: {response.json()}"
        
        # Checking if any data from an operator sheet wasn't updated
        login_operator_response = client.post("api/v1/auth/login", json={
            "email": "operator@gmail.com",
            "password": "senha123"
        })
        
        token_operator = login_operator_response.json()["access_token"]
        
        response_operator = client.get("api/v1/sheets/sheet123", 
            headers={"Authorization":f"Bearer {token_operator}"})

        assert response_operator.status_code == 200
        assert response_operator.json()["salary"] == 0
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        
def test_trying_to_access_without_authorization():
    db = TestingSessionLocal()
    Base.metadata.create_all(engine)
    
    try:
        response = client.post("api/v1/sheets/",
            json={
                "name": "testesheet",
                "initial_lines": 15,
                "goal": 20,
                "platform_id": "platform123",
                "cooperation_type": "META" 
            })
        assert response.status_code == 401
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        
def test_trying_to_access_with_an_invalid_token():
    db = TestingSessionLocal()
    Base.metadata.create_all(engine)
    
    try:  
        user = User(
            id="user123",
            email = "user@gmail.com",
            password_hash = hash_password("senha123"),
            is_active = True,
            plan_type = PlanType.LIFETIME,
        )
        db.add(user)
        db.commit()
        
        platform = Platform(
            id="platform123",
            name ="TestePlatform"
        )
        db.add(platform)
                
        sheet = Sheet(
            id="sheet123",
            name = "TestePlatform",
            goal = 20,
            cooperation_type = CooperationType.META,
            owner_id = "user123",
            status = SheetStatus.NOT_STARTED,
            platform_id = "platform123"
                    
        )
        db.add(sheet)
        db.commit()
       
        invalid_format_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9-eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjoxNzg4NTYxMjU3fQ-dRXdjuue7eIxG5W2khOR4H_s0nzEH7JtUiYHvNdWSHg"
       
        response_invalid_token = client.get("api/v1/sheets/", headers={"Authorization":f"Bearer {invalid_format_token}"})
    
    
        assert response_invalid_token.status_code == 401
    finally:
        db.close()
        Base.metadata.drop_all(engine)

def test_trying_to_access_with_an_expired_token():
    db = TestingSessionLocal()
    Base.metadata.create_all(engine)
    
    try:  
        user = User(
            id="user123",
            email = "user@gmail.com",
            password_hash = hash_password("senha123"),
            is_active = True,
            plan_type = PlanType.LIFETIME,
        )
        db.add(user)
        db.commit()
        
        platform = Platform(
            id="platform123",
            name ="TestePlatform"
        )
        db.add(platform)
                
        sheet = Sheet(
            id="sheet123",
            name = "TestePlatform",
            goal = 20,
            cooperation_type = CooperationType.META,
            owner_id = "user123",
            status = SheetStatus.NOT_STARTED,
            platform_id = "platform123"
                    
        )
        db.add(sheet)
        db.commit()
      
        expired_token =  create_access_token(
            data={"sub": "user123"},
            expires_delta=timedelta(seconds=-1)  
        )
        response_expired_token = client.get("api/v1/sheets/sheet123", headers={"Authorization":f"Bearer {expired_token}"})
        
    
        assert response_expired_token.status_code == 401
        
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        
        
def test_trying_to_delete_a_sheet_from_another_user():
    db = TestingSessionLocal()
    Base.metadata.create_all(engine)

    try:
        
        user = User(
            id="user123",
            email = "user@gmail.com",
            password_hash = hash_password("senha123"),
            is_active = True,
            plan_type = PlanType.LIFETIME,
        )
        db.add(user)
        
        operator = User(
            id="operator123",
            email ="operator@gmail.com",
            password_hash = hash_password("senha123"),
            is_active =True,
            plan_type = PlanType.LIFETIME,
            owner_id = "user123"
        )
        db.add(operator)
        db.commit()
        
        platform = Platform(
            id="platform123",
            name ="TestePlatform"
        )
        db.add(platform)
        
        sheet = Sheet(
            id="sheet123",
            name = "TestePlatform",
            goal = 20,
            cooperation_type = CooperationType.META,
            owner_id = "operator123",
            status = SheetStatus.NOT_STARTED,
            platform_id = "platform123"
            
        )
        db.add(sheet)
        db.commit()
        
        # Trying to delete a sheet from a user that isn't its owner
        login_response = client.post("api/v1/auth/login", json={
            "email": "user@gmail.com",
            "password": "senha123"
        })
        token = login_response.json()["access_token"]
        
        response = client.delete("api/v1/sheets/sheet123", 
            headers={"Authorization": f"Bearer {token}"} ,                      
        )
        assert response.status_code == 404 , f"Esperado 404 retornou {response.status_code}: {response.json()}"
        
        # Checking if any data from an operator sheet wasn't deleted
        login_operator_response = client.post("api/v1/auth/login", json={
            "email": "operator@gmail.com",
            "password": "senha123"
        })
        
        token_operator = login_operator_response.json()["access_token"]
        
        response_operator = client.get("api/v1/sheets/sheet123", 
            headers={"Authorization":f"Bearer {token_operator}"})
  
        assert response_operator.status_code == 200
        assert response_operator.json()["id"] == "sheet123"
    finally:
        db.close()
        Base.metadata.drop_all(engine)