# tests/test_schemas.py
import pytest
from datetime import datetime
from pydantic import ValidationError
from schemas import VectorClockSchema, FragmentCreate, FragmentResponse

class TestVectorClockSchema:
    def test_valid_clock(self):
        vc = VectorClockSchema(clock={"S1": 1, "S2": 3})
        assert vc.clock == {"S1": 1, "S2": 3}

    def test_empty_clock_is_allowed(self):
        vc = VectorClockSchema(clock={})
        assert vc.clock == {}

    def test_counter_zero_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            VectorClockSchema(clock={"S1": 0})
        assert "Counter for S1 must be int >= 1" in str(exc_info.value)

    def test_negative_counter_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            VectorClockSchema(clock={"S1": -5})
        assert "Counter for S1 must be int >= 1" in str(exc_info.value)

    def test_empty_node_id_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            VectorClockSchema(clock={"": 1})
        assert "Node ID must be non-empty string" in str(exc_info.value)

class TestFragmentCreate:
    def test_valid_without_vector_clock(self):
        frag = FragmentCreate(doc_id="doc1", content="Hello", node_id="S1")
        assert frag.vector_clock is None
        assert frag.doc_id == "doc1"

    def test_valid_with_vector_clock(self):
        frag = FragmentCreate(
            doc_id="doc1",
            content="Hi",
            node_id="S2",
            vector_clock=VectorClockSchema(clock={"S1": 2, "S2": 1})
        )
        assert frag.vector_clock.clock == {"S1": 2, "S2": 1}

    def test_invalid_missing_doc_id(self):
        with pytest.raises(ValidationError):
            FragmentCreate(content="x", node_id="S1")

    def test_invalid_empty_content(self):
        with pytest.raises(ValidationError):
            FragmentCreate(doc_id="doc1", content="", node_id="S1")

    def test_invalid_empty_node_id(self):
        with pytest.raises(ValidationError):
            FragmentCreate(doc_id="doc1", content="x", node_id="")

class TestFragmentResponse:
    def test_from_attributes(self):
        # Mô phỏng một object giống như SQLAlchemy model instance
        class MockFragment:
            id = 1
            doc_id = "d1"
            content = "Hello world"
            vector_clock = {"S1": 1}
            created_at = datetime(2025, 1, 1, 12, 0, 0)
            updated_at = datetime(2025, 1, 1, 12, 0, 0)

        resp = FragmentResponse.model_validate(MockFragment())
        assert resp.id == 1
        assert resp.vector_clock == {"S1": 1}
        assert resp.created_at.year == 2025