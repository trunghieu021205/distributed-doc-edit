# app/schemas.py
from pydantic import BaseModel, field_validator, model_validator
from typing import Dict, Optional
from datetime import datetime


class VectorClockSchema(BaseModel):
    clock: Dict[str, int]

    @field_validator('clock')
    @classmethod
    def validate_clock(cls, v: Dict[str, int]) -> Dict[str, int]:
        for node_id, counter in v.items():
            if not node_id or not node_id.strip():
                raise ValueError("Node ID must be non-empty string")
            if counter < 1:
                raise ValueError(f"Counter for {node_id} must be int >= 1")
        return v


class FragmentCreate(BaseModel):
    doc_id: str
    content: str
    node_id: str
    vector_clock: Optional[VectorClockSchema] = None

    @field_validator('content', 'node_id', 'doc_id')
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v


class FragmentUpdate(BaseModel):
    content: str
    node_id: str
    vector_clock: Dict[str, int]

    @field_validator('content', 'node_id')
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v


class FragmentResponse(BaseModel):
    id: int
    doc_id: str
    content: str
    vector_clock: Dict[str, int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}