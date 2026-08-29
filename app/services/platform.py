import uuid
from sqlalchemy.orm import Session
from app.models.platform import Platform
from app.repositories.platform import PlatformRepository
from app.exceptions.platform_exceptions import (
    PlatformAlreadyExistsException,
    PlatformNameEmptyException,
    PlatformNotFoundException,
)
import logging

logger = logging.getLogger(__name__)


def list_platforms(platform_repo: PlatformRepository) -> list[Platform]:
    return platform_repo.get_all_platforms()


def create_new_platform(platform_repo: PlatformRepository, db: Session, name: str) -> Platform:
    logger.info("Attempting to create platform")

    name = name.strip()
    if not name:
        logger.warning("Platform name cannot be empty.")
        raise PlatformNameEmptyException("Platform name cannot be empty.")

    existing = platform_repo.get_platform_by_name(name)
    if existing:
        logger.warning("Platform already exists.")
        raise PlatformAlreadyExistsException("Platform already exists.")

    new_platform = Platform(id=str(uuid.uuid4()), name=name)
    platform_repo.create_platform(new_platform)
    db.commit()
    db.refresh(new_platform)
    logger.info(f"Platform {new_platform.id} created")
    return new_platform


def remove_platform(platform_repo: PlatformRepository, db: Session, platform_id: str) -> None:
    logger.info("Attempting to remove platform")

    platform = platform_repo.get_platform_by_id(platform_id)
    if not platform:
        logger.warning("Platform not found.")
        raise PlatformNotFoundException("Platform not found.")

    platform_repo.delete_platform(platform)
    db.commit()
    logger.info(f"Platform {platform_id} deleted")
