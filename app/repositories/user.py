from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.activation_key import ActivationKey


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()
    
    # Specific methods for the role operator
    def get_operator_by_owner(self, owner_id: str) -> list[User]:
        return self.db.query(User).filter(
            User.owner_id == owner_id,
            User.role == UserRole.OPERADOR
        ).all()
    
    def get_operator_by_id(self, operator_id: str , owner_id: str) -> User | None:
        return self.db.query(User).filter(
            User.id == operator_id,
            User.owner_id == owner_id,
            User.role == UserRole.OPERADOR
        ).first()

    def create_user(self, user: User) -> User:
        self.db.add(user)
        return user

    def update_user(self, user: User) -> User:
        self.db.add(user)
        return user

class ActivationKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_key(self, activation_key: ActivationKey) -> ActivationKey:
        self.db.add(activation_key)
        return activation_key

    def get_activation_key(self, key: str) -> ActivationKey | None:
        return self.db.query(ActivationKey).filter(ActivationKey.key == key).first()

    def mark_key_as_used(self, activation_key: ActivationKey, user_id: str) -> ActivationKey:
        activation_key.is_used = True
        activation_key.used_by = user_id
        self.db.add(activation_key)
        return activation_key
