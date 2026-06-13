from sqlalchemy.orm import Session
from app.models.platform import Platform


def get_all_platforms(db: Session) -> list[Platform]:
    """Retorna todas as plataformas cadastradas, ordenadas por nome."""
    return db.query(Platform).order_by(Platform.name).all()



def get_platform_by_id(db:Session, platform_id: str) -> Platform | None:
    """Busca uma plataforma pelo ID"""
    return db.query(Platform).filter(Platform.id == platform_id).first()

def get_platform_by_name(db: Session, name: str) -> Platform | None:
    """Busca uma plataforma pelo nome (para evitar duplicatas).s"""
    return db.query(Platform).filter(Platform.name==name).first()


def create_platform(db: Session, platform: Platform) -> Platform:
    """Persiste uma nova plataforma no banco."""
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform


def delete_platform(db: Session, platform: Platform) -> None:
    """ Remove uma plataforma do banco"""
    db.delete(platform)
    db.commit()