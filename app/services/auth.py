from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.user import User, PlanType
from app.schemas.user import UserRegisterRequest, UserLoginRequest
from app.repositories.user import UserRepository, ActivationKeyRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.exceptions.user_exceptions import (
    UserEmailAlreadyExistsException,
    UserExpiredPlanException,
    UserInactiveAccountException,
    UserInvalidCredentialsException,
    InvalidKeyException,
    KeyAlreadyUsedException,
    KeyExpiredException,
)
import logging

logger = logging.getLogger(__name__)


def register_user(
    user_repo: UserRepository,
    key_repo: ActivationKeyRepository,
    db: Session,
    data: UserRegisterRequest,
) -> User:
    logger.info("Attempting user registration")

    existing_user = user_repo.get_user_by_email(data.email)
    if existing_user:
        logger.warning("Email already exists.")
        raise UserEmailAlreadyExistsException("Email already exists.")

    activation_key = key_repo.get_activation_key(data.activation_key)

    if not activation_key:
        logger.warning("Invalid Key.")
        raise InvalidKeyException("Invalid Key.")

    if activation_key.is_used:
        logger.warning("Key already used.")
        raise KeyAlreadyUsedException("Key already used.")

    if activation_key.expires_at and activation_key.expires_at < datetime.utcnow():
        logger.warning("key expired")
        raise KeyExpiredException("Key expired.")

    plan_expires_at = None
    if activation_key.type == PlanType.MONTHLY:
        plan_expires_at = datetime.utcnow() + timedelta(days=30)
    elif activation_key.type == PlanType.TRIAL:
        plan_expires_at = datetime.utcnow() + timedelta(days=7)
    # LIFETIME keys have no expiry — plan_expires_at stays None.

    new_user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        is_active=True,
        plan_type=activation_key.type,
        plan_expires_at=plan_expires_at,
    )

    user = user_repo.create_user(new_user)
    key_repo.mark_key_as_used(activation_key, user.id)

    db.commit()
    db.refresh(user)

    logger.info(f"User {user.id} registered")
    return user


def login_user(user_repo: UserRepository, db: Session, data: UserLoginRequest) -> dict:
    logger.info("Attempting login")

    user = user_repo.get_user_by_email(data.email)

    # Intentionally generic message — avoids leaking whether the email exists in the system.
    if not user or not verify_password(data.password, user.password_hash):
        logger.warning("Invalid Credentials.")
        raise UserInvalidCredentialsException("Invalid Credentials.")

    if not user.is_active:
        logger.warning("Inactive account.")
        raise UserInactiveAccountException("Inactive account.")

    if user.plan_expires_at and user.plan_expires_at < datetime.utcnow():
        logger.warning("Plan expired! Contact support.")
        raise UserExpiredPlanException("Plan expired! Contact support.")
    
    user.last_login = datetime.utcnow()
    user_repo.update_user(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": user.id})
    logger.info(f"User {user.id} logged in")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }
