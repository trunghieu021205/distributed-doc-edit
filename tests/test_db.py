# tests/test_db.py
from database import SessionLocal, engine, Base
from models import DocumentFragment
from sqlalchemy import inspect

def test_document_fragment_table_exists():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "document_fragments" in tables

def test_create_fragment():
    db = SessionLocal()
    fragment = DocumentFragment(
        doc_id="doc1",
        content="Hello",
        vector_clock={"S1": 1}
    )
    db.add(fragment)
    db.commit()
    db.refresh(fragment)
    assert fragment.id is not None
    assert fragment.vector_clock == {"S1": 1}
    db.delete(fragment)  # dọn dẹp
    db.commit()
    db.close()