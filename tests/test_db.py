# tests/test_db.py
"""
Test trực tiếp database layer dùng in-memory SQLite (qua fixture db_session).
Không phụ thuộc Postgres.
"""
import pytest
from sqlalchemy import inspect
from models import DocumentFragment


def test_document_fragment_table_exists(db_session):
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()
    assert "document_fragments" in tables


def test_create_fragment(db_session):
    fragment = DocumentFragment(
        doc_id="doc1",
        content="Hello",
        vector_clock={"S1": 1},
    )
    db_session.add(fragment)
    db_session.commit()
    db_session.refresh(fragment)

    assert fragment.id is not None
    assert fragment.vector_clock == {"S1": 1}

    # Cleanup
    db_session.delete(fragment)
    db_session.commit()


def test_fragment_fields(db_session):
    fragment = DocumentFragment(
        doc_id="doc2",
        content="World",
        vector_clock={"A": 2, "B": 1},
    )
    db_session.add(fragment)
    db_session.commit()
    db_session.refresh(fragment)

    assert fragment.doc_id == "doc2"
    assert fragment.content == "World"
    assert fragment.created_at is not None
    assert fragment.updated_at is not None