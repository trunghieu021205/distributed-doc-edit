# app/crud.py
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from models import DocumentFragment
from schemas import FragmentCreate
from vector_clock import VectorClock


def create_fragment(db: Session, frag_in: FragmentCreate) -> DocumentFragment:
    """Create new fragment. If client doesn't send vector_clock, initialize with {node_id: 1}."""
    if frag_in.vector_clock:
        initial_clock = frag_in.vector_clock.clock
    else:
        vc = VectorClock()
        vc.increment(frag_in.node_id)
        initial_clock = vc.to_dict()

    db_fragment = DocumentFragment(
        doc_id=frag_in.doc_id,
        content=frag_in.content,
        vector_clock=initial_clock,
    )
    db.add(db_fragment)
    db.commit()
    db.refresh(db_fragment)
    return db_fragment


def get_fragment(db: Session, frag_id: int) -> Optional[DocumentFragment]:
    """Get fragment by id, return None if not found."""
    return db.query(DocumentFragment).filter(DocumentFragment.id == frag_id).first()


def get_fragments_by_doc_id(db: Session, doc_id: str) -> List[DocumentFragment]:
    """Get all fragments by doc_id."""
    return db.query(DocumentFragment).filter(DocumentFragment.doc_id == doc_id).all()


def update_fragment(
    db: Session,
    frag_id: int,
    frag_in: FragmentCreate,
) -> Optional[DocumentFragment]:
    """
    Update fragment with vector clock logic:
    - Get current clock from DB
    - If client sends vector_clock, check for concurrent updates (conflict)
    - Merge client clock into DB clock
    - Increment the node_id counter
    """
    db_fragment = get_fragment(db, frag_id)
    if not db_fragment:
        return None

    current_clock = VectorClock.from_dict(db_fragment.vector_clock)

    if frag_in.vector_clock:
        client_clock = VectorClock.from_dict(frag_in.vector_clock.clock)
        # Only reject concurrent updates (true conflicts)
        # Causal updates (client is older) are allowed
        if client_clock.is_concurrent(current_clock):
            raise ValueError("Conflict: concurrent updates detected")
        current_clock.merge(client_clock)

    current_clock.increment(frag_in.node_id)

    db_fragment.content = frag_in.content
    db_fragment.vector_clock = current_clock.to_dict()
    db.commit()
    db.refresh(db_fragment)
    return db_fragment