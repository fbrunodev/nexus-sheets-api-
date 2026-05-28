from sqlalchemy.orm import Session
from app.models.user import User
from app.models.activation_key import ActivationKey
from datetime import datetime

#--------USER------------------------------------

def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Busca um usuário pelo email.
    Retorna o objeto User ou None se não encontrado
    """
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: str) -> User | None:
    """
    Busca um usuário pelo ID.
    Retorna o objeto User ou None se não encontrado
    """
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, user: User) -> User:
    """
    Persiste um novo usuário no banco de dados
    O objeto User já deve conter suas credenciais preenchidas
    """
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User) -> User:
    """
    Salva as alterações em um usuário existente.
    Usado para atualizar last_login, plan_type, is_active, etc.
    """

    db.commit()
    db.refresh(user)
    return user


#-----------ACTIVATION KEY------------------------------------
def get_activation_key(db: Session, key: str) -> ActivationKey | None:
    """
     Busca uma chave de ativação pelo valor da chave.
    Retorna o objeto ActivationKey ou None se não encontrada.
    """
    return db.query(ActivationKey).filter(ActivationKey.key == key).first()
    

def mark_key_as_used(db: Session, activation_key: ActivationKey, user_id: str) -> ActivationKey:
    """
    Marca uma chave de ativação como utilizada.
    Registra qual usuário a utilizou e quando
    """
    activation_key.is_used =True
    activation_key.used_by = user_id
    db.commit()
    db.refresh(activation_key)
    return activation_key