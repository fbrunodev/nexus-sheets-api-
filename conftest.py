# conftest.py
from app.core.logging_config import logging_config
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base

logging_config()


TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/nexus_test"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    
    
    yield session
    
    
    session.close()
    Base.metadata.drop_all(engine)
    