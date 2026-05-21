
import sys, os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(__file__))

from database import Base, engine as original_engine, SessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=original_engine)
    yield
