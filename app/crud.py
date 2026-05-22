from sqlalchemy.orm import Session
from models import DocumentFragment
from schemas import FragmentCreate
from vector_clock import VectorClock

def create_fragment(db: Session, fragment: FragmentCreate) -> DocumentFragment:
    if fragment.vector_clock:
        vc_dict = fragment.vector_clock.clock
    else:
        vc_dict = {fragment.node_id: 1}

    db_fragment = DocumentFragment(
        doc_id=fragment.doc_id,
        content=fragment.content,
        vector_clock=vc_dict
    )
    db.add(db_fragment)
    db.commit()
    db.refresh(db_fragment)
    return db_fragment

def get_fragment(db: Session, frag_id: int) -> DocumentFragment | None:
    return db.query(DocumentFragment).filter(DocumentFragment.id == frag_id).first()

def get_fragments_by_doc_id(db: Session, doc_id: str) -> list[DocumentFragment]:
    return db.query(DocumentFragment).filter(DocumentFragment.doc_id == doc_id).all()

def update_fragment(db: Session, frag_id: int, fragment_update: FragmentCreate) -> DocumentFragment | None:
    db_fragment = get_fragment(db, frag_id)
    if not db_fragment:
        return None

    current_clock = VectorClock.from_dict(db_fragment.vector_clock)

    if fragment_update.vector_clock:
        client_clock = VectorClock.from_dict(fragment_update.vector_clock.clock)
        current_clock.merge(client_clock)

    current_clock.increment(fragment_update.node_id)

    db_fragment.content = fragment_update.content
    db_fragment.vector_clock = current_clock.to_dict()
    db.commit()
    db.refresh(db_fragment)
    return db_fragment