from sqlalchemy.orm import Session
from app.models.platform import Platform



class PlatformRepository:
    
    def __init__(self, db: Session):
        self.db = db

    def get_all_platforms(self) -> list[Platform]:
        """Retorna todas as plataformas cadastradas, ordenadas por nome."""
        return self.db.query(Platform).order_by(Platform.name).all()



    def get_platform_by_id(self, platform_id: str) -> Platform | None:
        """Busca uma plataforma pelo ID"""
        return self.db.query(Platform).filter(Platform.id == platform_id).first()

    def get_platform_by_name(self, name: str) -> Platform | None:
        """Busca uma plataforma pelo nome (para evitar duplicatas).s"""
        return self.db.query(Platform).filter(Platform.name==name).first()


    def create_platform(self, platform: Platform) -> Platform:
        """Persiste uma nova plataforma no banco."""
        self.db.add(platform)
       
        return platform


    def delete_platform(self, platform: Platform) -> None:
        """ Remove uma plataforma do banco"""
        self.db.delete(platform)
        