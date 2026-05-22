# app/schemas.py
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

class VectorClockSchema(BaseModel):
    clock: Dict[str, int] = Field(
        default_factory=dict,
        description="Vector clock as dict of node_id -> counter (>=1)"
    )

    @field_validator('clock')
    @classmethod
    def counters_must_be_positive(cls, v: Dict[str, int]) -> Dict[str, int]:
        for node, counter in v.items():
            if not isinstance(node, str) or not node:
                raise ValueError(f'Node ID must be non-empty string, got {node!r}')
            if not isinstance(counter, int) or counter < 1:
                raise ValueError(f'Counter for {node} must be int >= 1, got {counter}')
        return v

class FragmentCreate(BaseModel):
    doc_id: str = Field(..., min_length=1, description="Document identifier")
    content: str = Field(..., min_length=1, description="Fragment content")
    node_id: str = Field(..., min_length=1, description="ID of the node performing the update (e.g. S1)")
    vector_clock: Optional[VectorClockSchema] = Field(
        None,
        description="Optional vector clock. If omitted, server initializes {node_id: 1}"
    )

class FragmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_id: str
    content: str
    vector_clock: Dict[str, int]
    created_at: datetime
    updated_at: datetime