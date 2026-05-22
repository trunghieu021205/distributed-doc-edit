# tests/conftest.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from main import app
from fastapi.testclient import TestClient

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    from database import get_db
    app.dependency_overrides[get_db] = override_get_db_func(db_session)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def override_get_db_func(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass
    return _override