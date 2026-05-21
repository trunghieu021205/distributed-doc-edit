# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from database import Base   

class DocumentFragment(Base):
    __tablename__ = "document_fragments"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True, nullable=False)
    content = Column(String, nullable=False)
    vector_clock = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())