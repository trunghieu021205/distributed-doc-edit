# tests/test_crud.py
import pytest
import crud
from schemas import FragmentCreate, VectorClockSchema

def test_create_fragment_without_clock(db_session):
    frag_in = FragmentCreate(doc_id="doc1", content="Hello", node_id="S1")
    frag = crud.create_fragment(db_session, frag_in)
    assert frag.id is not None
    assert frag.doc_id == "doc1"
    assert frag.content == "Hello"
    assert frag.vector_clock == {"S1": 1}

def test_create_fragment_with_clock(db_session):
    vc = VectorClockSchema(clock={"S1": 2, "S2": 1})
    frag_in = FragmentCreate(doc_id="doc2", content="World", node_id="S2", vector_clock=vc)
    frag = crud.create_fragment(db_session, frag_in)
    assert frag.vector_clock == {"S1": 2, "S2": 1}

def test_get_fragment_found(db_session):
    frag_in = FragmentCreate(doc_id="docX", content="X", node_id="S1")
    created = crud.create_fragment(db_session, frag_in)
    fetched = crud.get_fragment(db_session, created.id)
    assert fetched is not None
    assert fetched.content == "X"

def test_get_fragment_not_found(db_session):
    assert crud.get_fragment(db_session, 999) is None

def test_get_fragments_by_doc_id(db_session):
    crud.create_fragment(db_session, FragmentCreate(doc_id="shared", content="A", node_id="S1"))
    crud.create_fragment(db_session, FragmentCreate(doc_id="shared", content="B", node_id="S2"))
    crud.create_fragment(db_session, FragmentCreate(doc_id="other", content="C", node_id="S1"))
    shared = crud.get_fragments_by_doc_id(db_session, "shared")
    assert len(shared) == 2
    contents = {f.content for f in shared}
    assert contents == {"A", "B"}

def test_update_fragment_without_client_clock(db_session):
    frag_in = FragmentCreate(doc_id="up1", content="v1", node_id="S1")
    frag = crud.create_fragment(db_session, frag_in)
    # Cập nhật không gửi clock -> chỉ increment node S2
    update_in = FragmentCreate(doc_id="up1", content="v2", node_id="S2")
    updated = crud.update_fragment(db_session, frag.id, update_in)
    assert updated is not None
    assert updated.content == "v2"
    # Clock ban đầu {"S1":1}, sau khi merge (client không gửi clock), merge với clock rỗng thì không đổi,
    # rồi increment S2 -> {"S1":1, "S2":1}
    assert updated.vector_clock == {"S1": 1, "S2": 1}

def test_update_fragment_with_client_clock(db_session):
    # Tạo fragment với clock {"S1":1}
    frag = crud.create_fragment(db_session, FragmentCreate(doc_id="up2", content="start", node_id="S1"))
    # Client gửi clock cũ {"S1":1} và muốn nâng lên với node S2
    client_vc = VectorClockSchema(clock={"S1": 1})
    update_in = FragmentCreate(doc_id="up2", content="updated", node_id="S2", vector_clock=client_vc)
    updated = crud.update_fragment(db_session, frag.id, update_in)
    # Sau merge: DB {"S1":1} + client {"S1":1} -> {"S1":1}
    # Increment S2 -> {"S1":1, "S2":1}
    assert updated.vector_clock == {"S1": 1, "S2": 1}
    assert updated.content == "updated"

    # Tiếp tục cập nhật với node S1, client gửi clock cũ {"S1":1, "S2":1}
    client_vc2 = VectorClockSchema(clock={"S1": 1, "S2": 1})
    update_in2 = FragmentCreate(doc_id="up2", content="final", node_id="S1", vector_clock=client_vc2)
    updated2 = crud.update_fragment(db_session, frag.id, update_in2)
    # Merge: DB hiện tại {"S1":1, "S2":1}, client gửi {"S1":1, "S2":1} -> không đổi
    # Increment S1 -> {"S1":2, "S2":1}
    assert updated2.vector_clock == {"S1": 2, "S2": 1}
    assert updated2.content == "final"

def test_update_fragment_not_found(db_session):
    update_in = FragmentCreate(doc_id="ghost", content="x", node_id="S1")
    result = crud.update_fragment(db_session, 999, update_in)
    assert result is None