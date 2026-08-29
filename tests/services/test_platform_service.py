import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.models.platform import Platform
from app.schemas.platform import PlatformCreate
from app.exceptions.platform_exceptions import PlatformAlreadyExistsException, PlatformNameEmptyException,PlatformNotFoundException
from app.services.platform import create_new_platform, remove_platform



class PlatformRepositoryFake:
    
    def __init__(self):
        self.platforms = {}

    def get_all_platforms(self) -> list[Platform]:
        return list(self.platforms.values())



    def get_platform_by_id(self, platform_id: str) -> Platform | None:
        """Busca uma plataforma pelo ID"""
        for platform in self.platforms.values():
            if platform.id == platform_id:
                return platform
        return None

    def get_platform_by_name(self, name: str) -> Platform | None:
        """Busca uma plataforma pelo nome (para evitar duplicatas).s"""
        for platform in self.platforms.values():
            if platform.name == name:
                return platform
        return None

    def create_platform(self, platform: Platform) -> Platform:
        """Persiste uma nova plataforma no banco."""
        self.platforms[platform.id] = platform
       
        return platform


    def delete_platform(self, platform: Platform) -> None:
        """ Remove uma plataforma do banco"""
        self.platforms.pop(platform.id, None)
        
        
        






#------------------------------------- TEST EXCEPTIONS------------------------------------------------------------

def test_create_platform_already_exists_exception():
    platform_repo = PlatformRepositoryFake()
    db_mock = MagicMock()
    
    data = Platform(
        id= "platform123",
        name = "Test",
        created_at = datetime.utcnow()
    )
    
    platform_repo.create_platform(data)
    
    with pytest.raises(PlatformAlreadyExistsException):
        
        create_new_platform(platform_repo, db=db_mock, name="Test")
        
        
def test_create_platform_empty_name_exception():
    platform_repo = PlatformRepositoryFake()
    db_mock = MagicMock()
    
    with pytest.raises(PlatformNameEmptyException):
        create_new_platform(platform_repo, db=db_mock, name="")
        
        
def test_platform_not_found_exception():
    platform_repo = PlatformRepositoryFake()
    db_mock = MagicMock()
    
    
    with pytest.raises(PlatformNotFoundException):
        remove_platform(platform_repo, db=db_mock, platform_id=2)