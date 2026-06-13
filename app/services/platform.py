import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.platform import Platform
from app.repositories.platform import(
    get_all_platforms,
    get_platform_by_id,
    get_platform_by_name,
    create_platform,
    delete_platform,
)


def list_platforms(db: Session) -> list[Platform]:
    """Lista todas as plataformas cadastradas."""
    return get_all_platforms(db)

def create_new_platform(db: Session, name: str) -> Platform:
    """
    Cria nova plataforma.
    Valida que o nome não está vazio e que não existe duplicada.
    """

    name = name.strip()


    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nome da plataforma não pode ser vazio"

        )

    # Verifica duplicata

    existing = get_platform_by_name(db, name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="já existe uma plataforma com esse nome."
        )

    new_platform = Platform(id=str(uuid.uuid4()), name=name)
    return create_platform(db, new_platform)


def remove_platform(db: Session, platform_id: str) -> None:
    """Remove uma plataforma pelo ID."""
    platform = get_platform_by_id(db, platform_id)
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plataforma não encontrada"
        )