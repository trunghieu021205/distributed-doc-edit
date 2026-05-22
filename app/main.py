# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import crud, schemas

app = FastAPI(title="Document Fragment Sync API")


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