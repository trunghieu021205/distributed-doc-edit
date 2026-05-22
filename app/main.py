# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import crud, schemas
from vector_clock import VectorClock

app = FastAPI(
    title="Distributed Doc Edit — Vector Clock API",
    description="Track causality & detect concurrent conflicts in a multi-master document system.",
    version="0.6.0",
)


@app.post("/fragments", response_model=schemas.FragmentResponse, status_code=201)
def create_fragment(payload: schemas.FragmentCreate, db: Session = Depends(get_db)):
    fragment = crud.create_fragment(db, payload)
    return fragment


@app.get("/fragments/{doc_id}", response_model=List[schemas.FragmentResponse])
def get_fragments(doc_id: str, db: Session = Depends(get_db)):
    return crud.get_fragments_by_doc_id(db, doc_id)


@app.put("/fragments/{frag_id}", response_model=schemas.FragmentResponse)
def update_fragment(frag_id: int, payload: schemas.FragmentUpdate, db: Session = Depends(get_db)):
    """
    Endpoint update nhận FragmentUpdate (content, node_id, vector_clock dict).
    Chuyển sang FragmentCreate.model_construct để tránh validate doc_id rỗng,
    vì doc_id không cần thiết khi update (fragment đã tồn tại).
    """
    vc_schema = (
        schemas.VectorClockSchema(clock=payload.vector_clock)
        if payload.vector_clock
        else None
    )
    frag_in = schemas.FragmentCreate.model_construct(
        doc_id="__update__",
        content=payload.content,
        node_id=payload.node_id,
        vector_clock=vc_schema,
    )
    try:
        fragment = crud.update_fragment(db, frag_id, frag_in)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if fragment is None:
        raise HTTPException(status_code=404, detail="Fragment not found")
    return fragment

@app.post("/fragments/compare", response_model=schemas.CompareResponse)
def compare_clocks(payload: schemas.CompareRequest):
    """
    So sánh quan hệ nhân quả giữa hai vector clock.
 
    **Metric chính của đề tài**: phân loại đúng Concurrent vs Causal.
 
    - `concurrent`  → hai site update cùng lúc, không biết nhau → Branch/Conflict
    - `a_before_b`  → A là nguyên nhân của B (causal, không conflict)
    - `b_before_a`  → B là nguyên nhân của A (causal, không conflict)
    - `equal`       → hai clock giống hệt nhau
    """
    vc_a = VectorClock.from_dict(payload.clock_a)
    vc_b = VectorClock.from_dict(payload.clock_b)
 
    if payload.clock_a == payload.clock_b:
        relation = "equal"
        is_concurrent = False
        explanation = "Hai vector clock giống nhau — cùng phiên bản, không có divergence."
    elif vc_a.happens_before(vc_b):
        relation = "a_before_b"
        is_concurrent = False
        explanation = (
            "A → B: A xảy ra trước B. "
            "B đã biết về A trước khi thực hiện update → Causal Update, không phải conflict."
        )
    elif vc_b.happens_before(vc_a):
        relation = "b_before_a"
        is_concurrent = False
        explanation = (
            "B → A: B xảy ra trước A. "
            "A đã biết về B trước khi thực hiện update → Causal Update, không phải conflict."
        )
    else:
        relation = "concurrent"
        is_concurrent = True
        explanation = (
            "A ∥ B: Hai update xảy ra song song — không có quan hệ nhân quả. "
            "Đây là Concurrent Update → tạo ra Branch/Conflict, cần giải quyết thủ công."
        )
 
    return schemas.CompareResponse(
        clock_a=payload.clock_a,
        clock_b=payload.clock_b,
        relation=relation,
        is_concurrent=is_concurrent,
        explanation=explanation,
    )
 
 
@app.get("/fragments/{doc_id}/analysis", response_model=schemas.DocumentAnalysis)
def analyze_document(doc_id: str, db: Session = Depends(get_db)):
    """
    Phân tích tất cả fragment của một document.
 
    Duyệt mọi cặp (i, j) và phân loại quan hệ vector clock:
    - Concurrent pairs → conflict branches cần giải quyết
    - Causal pairs     → updates có thứ tự nhân quả rõ ràng
    """
    fragments = crud.get_fragments_by_doc_id(db, doc_id)
    if not fragments:
        raise HTTPException(status_code=404, detail=f"No fragments found for doc '{doc_id}'")
 
    concurrent_pairs: list[schemas.ConflictPair] = []
    causal_pairs: list[schemas.ConflictPair] = []
    equal_pairs: list[schemas.ConflictPair] = []
 
    for i in range(len(fragments)):
        for j in range(i + 1, len(fragments)):
            fa, fb = fragments[i], fragments[j]
            vc_a = VectorClock.from_dict(fa.vector_clock)
            vc_b = VectorClock.from_dict(fb.vector_clock)
 
            if fa.vector_clock == fb.vector_clock:
                relation = "equal"
            elif vc_a.happens_before(vc_b):
                relation = "a_before_b"
            elif vc_b.happens_before(vc_a):
                relation = "b_before_a"
            else:
                relation = "concurrent"
 
            pair = schemas.ConflictPair(
                frag_a_id=fa.id,
                frag_b_id=fb.id,
                clock_a=fa.vector_clock,
                clock_b=fb.vector_clock,
                relation=relation,
            )
 
            if relation == "concurrent":
                concurrent_pairs.append(pair)
            elif relation == "equal":
                equal_pairs.append(pair)
            else:
                causal_pairs.append(pair)
 
    conflict_count = len(concurrent_pairs)
    summary = (
        f"Document '{doc_id}': {len(fragments)} fragments, "
        f"{conflict_count} conflict branch(es), "
        f"{len(causal_pairs)} causal pair(s)."
    )
 
    return schemas.DocumentAnalysis(
        doc_id=doc_id,
        total_fragments=len(fragments),
        concurrent_pairs=concurrent_pairs,
        causal_pairs=causal_pairs,
        equal_pairs=equal_pairs,
        conflict_count=conflict_count,
        summary=summary,
    )