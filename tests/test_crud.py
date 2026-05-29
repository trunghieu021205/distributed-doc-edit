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
    # Update without sending clock -> only increment node S2
    update_in = FragmentCreate(doc_id="up1", content="v2", node_id="S2")
    updated = crud.update_fragment(db_session, frag.id, update_in)
    assert updated is not None
    assert updated.content == "v2"
    # Clock initially {"S1":1}, after merge (client doesn't send clock), merge with empty clock doesn't change,
    # then increment S2 -> {"S1":1, "S2":1}
    assert updated.vector_clock == {"S1": 1, "S2": 1}

def test_update_fragment_with_client_clock(db_session):
    # Create fragment with clock {"S1":1}
    frag = crud.create_fragment(db_session, FragmentCreate(doc_id="up2", content="start", node_id="S1"))
    # Client sends old clock {"S1":1} and wants to upgrade with node S2
    client_vc = VectorClockSchema(clock={"S1": 1})
    update_in = FragmentCreate(doc_id="up2", content="updated", node_id="S2", vector_clock=client_vc)
    updated = crud.update_fragment(db_session, frag.id, update_in)
    # After merge: DB {"S1":1} + client {"S1":1} -> {"S1":1}
    # Increment S2 -> {"S1":1, "S2":1}
    assert updated.vector_clock == {"S1": 1, "S2": 1}
    assert updated.content == "updated"

    # Continue update with node S1, client sends old clock {"S1":1, "S2":1}
    client_vc2 = VectorClockSchema(clock={"S1": 1, "S2": 1})
    update_in2 = FragmentCreate(doc_id="up2", content="final", node_id="S1", vector_clock=client_vc2)
    updated2 = crud.update_fragment(db_session, frag.id, update_in2)
    # Merge: DB current {"S1":1, "S2":1}, client sends {"S1":1, "S2":1} -> no change
    # Increment S1 -> {"S1":2, "S2":1}
    assert updated2.vector_clock == {"S1": 2, "S2": 1}
    assert updated2.content == "final"

def test_update_fragment_not_found(db_session):
    update_in = FragmentCreate(doc_id="ghost", content="x", node_id="S1")
    result = crud.update_fragment(db_session, 999, update_in)
    assert result is None

def test_update_fragment_concurrent_conflict(db_session):
    """Test that concurrent updates are detected as conflicts (main requirement)"""
    # Create fragment with clock {"S1": 1}
    frag = crud.create_fragment(db_session, FragmentCreate(doc_id="conflict", content="original", node_id="S1"))
    
    # Simulate concurrent update from S2 that doesn't know about S1's update
    # S2 has clock {"S2": 1} which is concurrent with DB clock {"S1": 1}
    client_vc = VectorClockSchema(clock={"S2": 1})
    update_in = FragmentCreate(doc_id="conflict", content="concurrent_edit", node_id="S2", vector_clock=client_vc)
    
    # Should raise ValueError for concurrent updates
    with pytest.raises(ValueError, match="Conflict: concurrent updates detected"):
        crud.update_fragment(db_session, frag.id, update_in)

def test_update_fragment_causal_allowed(db_session):
    """Test that causal updates (client is older) are allowed"""
    # Create fragment with clock {"S1": 2}
    frag = crud.create_fragment(db_session, FragmentCreate(doc_id="causal", content="v1", node_id="S1"))
    # Update to {"S1": 2, "S2": 1}
    client_vc = VectorClockSchema(clock={"S1": 2})
    update_in = FragmentCreate(doc_id="causal", content="v2", node_id="S2", vector_clock=client_vc)
    crud.update_fragment(db_session, frag.id, update_in)
    
    # Now DB has {"S1": 2, "S2": 1}
    # Client with older clock {"S1": 2} tries to update - this is causal, should be allowed
    frag = crud.get_fragment(db_session, frag.id)
    client_vc_old = VectorClockSchema(clock={"S1": 2, "S2": 1})
    update_in_old = FragmentCreate(doc_id="causal", content="v3", node_id="S1", vector_clock=client_vc_old)
    
    # Should NOT raise error - causal updates are allowed
    updated = crud.update_fragment(db_session, frag.id, update_in_old)
    assert updated is not None
    assert updated.content == "v3"