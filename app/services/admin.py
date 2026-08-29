from sqlalchemy.orm import Session
from app.models.activation_key import ActivationKey
from app.models.user import PlanType
from app.schemas.admin import ActivationKeyCreate
import uuid
import random
import string
from app.repositories.user import ActivationKeyRepository
from app.exceptions.user_exceptions import ActivationKeyGenerationException
import logging

logger = logging.getLogger(__name__)


def generate_key_string() -> str:
    # Excludes visually ambiguous characters (0/O, 1/I) to prevent user confusion.
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("0", "").replace("O", "").replace("1", "").replace("I", "")

    def segment() -> str:
        return "".join(random.choices(chars, k=4))

    return f"NX-{segment()}-{segment()}-{segment()}"


def list_activation_keys(db: Session) -> list[ActivationKey]:
    return (
        db.query(ActivationKey)
        .order_by(ActivationKey.created_at.desc())
        .all()
    )


def create_activation_key(
    key_repo: ActivationKeyRepository, db: Session, data: ActivationKeyCreate
) -> ActivationKey:
    logger.info("Attempting to create activation key")

    # Retry up to 5 times to handle the astronomically unlikely case of a collision.
    for _ in range(5):
        key_string = generate_key_string()

        if not key_repo.get_activation_key(key_string):
            new_key = ActivationKey(
                id=str(uuid.uuid4()),
                key=key_string,
                type=data.type,
                expires_at=data.expires_at,
                is_used=False,
            )
            key_repo.create_key(new_key)
            db.commit()
            db.refresh(new_key)
            logger.info(f"Activation key {new_key.id} created")
            return new_key

    logger.warning("Failed to generate a unique activation key after 5 attempts")
    raise ActivationKeyGenerationException("Failed to create key.")
