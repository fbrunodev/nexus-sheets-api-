import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.models.activation_key import ActivationKey
from app.models.user import User, PlanType, UserRole
from app.schemas.admin import ActivationKeyCreate
from app.services.auth import register_user, login_user
from app.services.operator import soft_delete_operator
from app.schemas.user import UserRegisterRequest, UserLoginRequest
from app.services.admin import create_activation_key
from app.exceptions.user_exceptions import (
    UserInvalidCredentialsException,
    UserInactiveAccountException,
    UserExpiredPlanException,
    UserEmailAlreadyExistsException,
    OperatorNotFoundException,
    InvalidKeyException,
    KeyAlreadyUsedException,
    KeyExpiredException
)
from app.core.security import hash_password

class UserRepositoryFake:
    def __init__(self):
        self.users = {}

    def get_user_by_email(self, email: str) -> User | None:
        for user in self.users.values():
            if user.email == email:
                return user
        return None     
       
    def get_user_by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)
    
    def get_operator_by_id(self, operator_id: str, owner_id : str) -> User | None:
        operator = self.users.get(operator_id)
        if operator and operator.owner_id== owner_id:
            return operator
        return None
            
        
    def create_user(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def update_user(self, user: User) -> User:
        self.users[user.id] = user
        return user

    
    
class ActivationKeyRepositoryFake:
    def __init__(self):
        self.keys = {}

    def create_key(self, activation_key: ActivationKey) -> ActivationKey:
        self.keys[activation_key.id] = activation_key
        return activation_key

    def get_activation_key(self, key: str) -> ActivationKey | None:
        for activation_key in self.keys.values():
            if activation_key.key == key:
                return activation_key
        return None

    def mark_key_as_used(self, activation_key: ActivationKey, user_id: str) -> ActivationKey:
        activation_key.is_used = True
        activation_key.used_by = user_id
        self.keys[activation_key.id] = activation_key
        return activation_key


def test_register_user():
    user_repo = UserRepositoryFake()
    key_repo = ActivationKeyRepositoryFake()
    db_mock = MagicMock()

    key = ActivationKey(
        id="key1",
        key="abcd",
        type=PlanType.LIFETIME,
        is_used=False,
        created_at=datetime.utcnow(),
    )
    key_repo.create_key(key)

    data = UserRegisterRequest(email="user@gmail.com", password="addb", activation_key="abcd")

    result = register_user(user_repo, key_repo, db=db_mock, data=data)

    assert result.email == "user@gmail.com"
    assert key_repo.get_activation_key("abcd").is_used
    
def test_register_user_already_exists():
    user_repo = UserRepositoryFake()
    key_repo = ActivationKeyRepositoryFake()
    db_mock = MagicMock()

    key = ActivationKey(
        id="key1",
        key="abcd",
        type=PlanType.LIFETIME,
        is_used=False,
        created_at=datetime.utcnow(),
    )
    key_repo.create_key(key)
    user = User(
        id="user123",
        email="user@gmail.com",
        password_hash=hash_password("1234"),
        is_active = True,
        created_at = datetime.utcnow()
        
    )
    user_repo.create_user(user)
    
    data = UserRegisterRequest(email="user@gmail.com", password="addb", activation_key="abcd")

    with pytest.raises(UserEmailAlreadyExistsException):
        register_user(user_repo, key_repo, db=db_mock, data=data)

    
def test_register_key_already_used():
    user_repo = UserRepositoryFake()
    key_repo = ActivationKeyRepositoryFake()
    db_mock = MagicMock()

    key = ActivationKey(
        id="key1",
        key="abcd",
        type=PlanType.LIFETIME,
        is_used=True,
        created_at=datetime.utcnow(),
    )
    key_repo.create_key(key)
    
    
    data = UserRegisterRequest(email="user2@gmail.com", password="addb", activation_key="abcd")

    with pytest.raises(KeyAlreadyUsedException):
        register_user(user_repo, key_repo, db=db_mock, data=data)    

def test_register_invalid_key():
    user_repo = UserRepositoryFake()
    key_repo = ActivationKeyRepositoryFake()
    db_mock = MagicMock()

    
    
    data = UserRegisterRequest(email="user2@gmail.com", password="addb", activation_key="abcde")

    with pytest.raises(InvalidKeyException):
        register_user(user_repo, key_repo, db=db_mock, data=data)    
    
    
def test_register_key_expired():
    user_repo = UserRepositoryFake()
    key_repo = ActivationKeyRepositoryFake()
    db_mock = MagicMock()

    key = ActivationKey(
        id="key1",
        key="abcde",
        type=PlanType.TRIAL,
        is_used=False,
        expires_at=datetime.utcnow() - timedelta(days=1)
    )
    key_repo.create_key(key)
    
    
    data = UserRegisterRequest(email="user2@gmail.com", password="addb", activation_key="abcde")

    with pytest.raises(KeyExpiredException):
        register_user(user_repo, key_repo, db=db_mock, data=data)    

def test_create_key():
    key_repo = ActivationKeyRepositoryFake()
    db_mock = MagicMock()

    data = ActivationKeyCreate(type=PlanType.LIFETIME)
    result = create_activation_key(key_repo, db=db_mock, data=data)

    assert result.type == PlanType.LIFETIME

def test_delete_operator_not_found():
    user_repo = UserRepositoryFake()
    db_mock = MagicMock()
    
    with pytest.raises(OperatorNotFoundException):
        soft_delete_operator(user_repo, db=db_mock, operator_id="123123", owner_id="owner123")
    
def test_delete_operator():
    user_repo = UserRepositoryFake()
    db_mock = MagicMock()
    user_owner = User(id="owner123", email="user@gmail.com", password_hash="232", is_active=True)
    user_repo.create_user(user_owner)
    
    operator = User(id="operator123", email="operator@gmail.com" , password_hash ="21312",  is_active = True , owner_id = "owner123")
    user_repo.create_user(operator)
    
    soft_delete_operator(user_repo, db=db_mock, operator_id="operator123", owner_id="owner123")
    deleted =  user_repo.get_operator_by_id(operator_id="operator123", owner_id="owner123")
    assert deleted.is_active is False
    
    
# --- Login tests -------------------------------------------------------------------

def test_login_user():
    user_repo = UserRepositoryFake()
    db_mock = MagicMock()

    user = User(
        id="user123",
        email="user@test.com",
        password_hash=hash_password("secret"),
        is_active=True,
        plan_type=PlanType.LIFETIME,
        plan_expires_at=None,
    )
    user_repo.create_user(user)

    data = UserLoginRequest(email="user@test.com", password="secret")
    result = login_user(user_repo, db=db_mock, data=data)

    assert result["access_token"] is not None
    assert result["token_type"] == "bearer"
    assert result["user"].email == "user@test.com"


def test_login_invalid_credentials():
    user_repo = UserRepositoryFake()
    db_mock = MagicMock()

    data = UserLoginRequest(email="nobody@test.com", password="wrong")

    with pytest.raises(UserInvalidCredentialsException):
        login_user(user_repo, db=db_mock, data=data)


def test_login_wrong_password():
    
    user_repo = UserRepositoryFake()
    db_mock = MagicMock()

    user = User(
        id="user123",
        email="user@test.com",
        password_hash=hash_password("secret"),
        is_active=True,
        plan_type=PlanType.LIFETIME,
        plan_expires_at=None,
    )
    user_repo.create_user(user)

    data = UserLoginRequest(email="user@test.com", password="wrongpassword")

    with pytest.raises(UserInvalidCredentialsException):
        login_user(user_repo, db=db_mock, data=data)


def test_login_inactive_account():

    user_repo = UserRepositoryFake()
    db_mock = MagicMock()

    user = User(
        id="user123",
        email="user@test.com",
        password_hash=hash_password("secret"),
        is_active=False,
        plan_type=PlanType.LIFETIME,
        plan_expires_at=None,
    )
    user_repo.create_user(user)

    data = UserLoginRequest(email="user@test.com", password="secret")

    with pytest.raises(UserInactiveAccountException):
        login_user(user_repo, db=db_mock, data=data)


def test_login_expired_plan():
   
    user_repo = UserRepositoryFake()
    db_mock = MagicMock()

    user = User(
        id="user123",
        email="user@test.com",
        password_hash=hash_password("secret"),
        is_active=True,
        plan_type=PlanType.MONTHLY,
        plan_expires_at=datetime.utcnow() - timedelta(days=1),
    )
    user_repo.create_user(user)

    data = UserLoginRequest(email="user@test.com", password="secret")

    with pytest.raises(UserExpiredPlanException):
        login_user(user_repo, db=db_mock, data=data)

