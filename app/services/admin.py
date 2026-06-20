from sqlalchemy.orm import Session
from app.models.activation_key import ActivationKey
from app.models.user import PlanType
from app.schemas.admin import ActivationKeyCreate
from fastapi import HTTPException, status
import uuid
import random
import string


def generate_key_string() -> str:
    """
    Gera uma chave de ativação no formato NX-XXXX-XXXX-XXXX.
    Usa apenas letras maiúsculas e números para evitar confusão
    entre caracteres similares (0/O, 1/I, etc).
    """
    chars = string.ascii_uppercase + string.digits
    # Remove caracteres confusos
    chars = chars.replace("0", "").replace("O", "").replace("1", "").replace("I", "")

    def segment() -> str:
        return "".join(random.choices(chars, k=4))

    return f"NX-{segment()}-{segment()}-{segment()}"


def list_activation_keys(db: Session) -> list[ActivationKey]:
    """Retorna todas as activation keys ordenadas por data de criação."""
    return (
        db.query(ActivationKey)
        .order_by(ActivationKey.created_at.desc())
        .all()
    )


def create_activation_key(db: Session, data: ActivationKeyCreate) -> ActivationKey:
    """
    Gera uma nova activation key única.
    Tenta até 5 vezes para garantir que a key seja única.
    """
    
    # Tenta gerar uma key única — colisões são raras mas possíveis
    for _ in range(5):
        key_string = generate_key_string()

        # Verifica se a key já existe no banco
        existing = db.query(ActivationKey).filter(
            ActivationKey.key == key_string
        ).first()

        if not existing:
            # Key única encontrada — persiste e retorna
            new_key = ActivationKey(
                id=str(uuid.uuid4()),
                key=key_string,
                type=data.type,
                expires_at=data.expires_at,
                is_used=False,
            )
            db.add(new_key)
            db.commit()
            db.refresh(new_key)
            return new_key

    # Se após 5 tentativas não gerou key única — situação extremamente rara
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Erro ao gerar chave de ativação. Tente novamente."
    )