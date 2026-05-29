# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from typing import List, Dict, Any

# Import cho database
from database import get_db, engine, Base

import crud, schemas
from vector_clock import VectorClock

import time
from sqlalchemy import text

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Retry connect to DB
    max_retries = 10
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully")
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ Failed to connect to database after {max_retries} attempts")
                raise
            print(f"⏳ Waiting for database... ({attempt + 1}/{max_retries})")
            time.sleep(2)

    yield

app = FastAPI(
    title="Document Fragment Sync API",
    description="Distributed document update tracking system using Vector Clocks for conflict detection.",
    version="1.0.0",
    lifespan=lifespan,
)
# ---------------------------- Utility function ----------------------------

def analyze_fragments(fragments: List[Any]) -> Dict[str, Any]:
    """
    Analyze fragment list, return concurrent, causal, equal pairs and total conflict count.
    Can be used for both analysis endpoint and demo page.
    """
    concurrent_pairs = []
    causal_pairs = []
    equal_pairs = []

    n = len(fragments)
    for i in range(n):
        for j in range(i + 1, n):
            fa = fragments[i]
            fb = fragments[j]
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

            pair = {
                "frag_a_id": fa.id,
                "frag_b_id": fb.id,
                "clock_a": fa.vector_clock,
                "clock_b": fb.vector_clock,
                "relation": relation,
            }

            if relation == "concurrent":
                concurrent_pairs.append(pair)
            elif relation == "equal":
                equal_pairs.append(pair)
            else:
                causal_pairs.append(pair)

    conflict_count = len(concurrent_pairs)
    summary = (
        f"Document '{fragments[0].doc_id}': {n} fragments, "
        f"{conflict_count} conflict branch(es), "
        f"{len(causal_pairs)} causal pair(s)."
    ) if fragments else "No fragments."

    return {
        "doc_id": fragments[0].doc_id if fragments else "",
        "total_fragments": n,
        "concurrent_pairs": concurrent_pairs,
        "causal_pairs": causal_pairs,
        "equal_pairs": equal_pairs,
        "conflict_count": conflict_count,
        "summary": summary,
    }


# ---------------------------- Fragments CRUD ----------------------------

@app.post("/fragments", response_model=schemas.FragmentResponse, status_code=201,
          tags=["Fragments"], summary="Create new fragment")
def create_fragment(payload: schemas.FragmentCreate, db: Session = Depends(get_db)):
    """
    Create a text fragment with vector clock.
    If vector_clock is not provided, system will create default clock {node_id: 1}.
    """
    fragment = crud.create_fragment(db, payload)
    return fragment


@app.get("/fragments/{doc_id}", response_model=List[schemas.FragmentResponse],
         tags=["Fragments"], summary="Get all fragments for a document")
def get_fragments(doc_id: str, db: Session = Depends(get_db)):
    """Return list of fragments belonging to document with given `doc_id`."""
    return crud.get_fragments_by_doc_id(db, doc_id)


@app.put("/fragments/{frag_id}", response_model=schemas.FragmentResponse,
         tags=["Fragments"], summary="Update fragment")
def update_fragment(frag_id: int, payload: schemas.FragmentUpdate, db: Session = Depends(get_db)):
    """
    Update fragment content and vector clock.
    Used to synchronize changes from sites.
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


# ---------------------------- Analysis Endpoints ----------------------------

@app.post("/fragments/compare", response_model=schemas.CompareResponse,
          tags=["Analysis"], summary="Compare two vector clocks")
def compare_clocks(payload: schemas.CompareRequest):
    """
    **Main metric of the project**: Classify causal relationship between two vector clocks.

    - `concurrent`  → Two parallel updates, create Branch/Conflict.
    - `a_before_b`  → A happens before B (causal).
    - `b_before_a`  → B happens before A (causal).
    - `equal`       → Two clocks are identical.
    """
    vc_a = VectorClock.from_dict(payload.clock_a)
    vc_b = VectorClock.from_dict(payload.clock_b)

    if payload.clock_a == payload.clock_b:
        relation = "equal"
        is_concurrent = False
        explanation = "Two vector clocks are identical – same version."
    elif vc_a.happens_before(vc_b):
        relation = "a_before_b"
        is_concurrent = False
        explanation = "A → B: A is cause of B. B knows about A → Causal Update, no conflict."
    elif vc_b.happens_before(vc_a):
        relation = "b_before_a"
        is_concurrent = False
        explanation = "B → A: B is cause of A. A knows about B → Causal Update, no conflict."
    else:
        relation = "concurrent"
        is_concurrent = True
        explanation = "A ∥ B: Two independent updates, unaware of each other → Concurrent Update → Conflict."

    return schemas.CompareResponse(
        clock_a=payload.clock_a,
        clock_b=payload.clock_b,
        relation=relation,
        is_concurrent=is_concurrent,
        explanation=explanation,
    )


@app.get("/fragments/{doc_id}/analysis", response_model=schemas.DocumentAnalysis,
         tags=["Analysis"], summary="Analyze entire document")
def analyze_document(doc_id: str, db: Session = Depends(get_db)):
    """
    Scan all fragments of a document, determine pairs with relationships:
    - **Concurrent** (conflict) – needs resolution.
    - **Causal** (before – after) – no conflict.
    - **Equal** (identical).

    Return summary report.
    """
    fragments = crud.get_fragments_by_doc_id(db, doc_id)
    if not fragments:
        raise HTTPException(status_code=404, detail=f"No fragments found for doc '{doc_id}'")

    analysis = analyze_fragments(fragments)
    return schemas.DocumentAnalysis(**analysis)


# ---------------------------- Demo UI ----------------------------

@app.get("/demo/{doc_id}", response_class=HTMLResponse,
         tags=["Demo"], summary="Visual demo interface")
def demo_page(doc_id: str, db: Session = Depends(get_db)):
    """
    Simple web page displaying conflict analysis results for a document.
    Used for presentation or quick testing.
    """
    fragments = crud.get_fragments_by_doc_id(db, doc_id)
    if not fragments:
        return HTMLResponse(content=f"<h2>Document '{doc_id}' does not exist.</h2>", status_code=404)

    analysis = analyze_fragments(fragments)
    # Generate HTML
    concurrent_html = ""
    for p in analysis["concurrent_pairs"]:
        concurrent_html += (
            f'<div class="pair conflict">'
            f'<span class="fragment-id">Fragment {p["frag_a_id"]}</span> '
            f'<span class="clock">{p["clock_a"]}</span> '
            f'<span class="relation concurrent">↔</span> '
            f'<span class="fragment-id">Fragment {p["frag_b_id"]}</span> '
            f'<span class="clock">{p["clock_b"]}</span>'
            f'</div>'
        )
    causal_html = ""
    for p in analysis["causal_pairs"]:
        arrow = "→" if p["relation"] == "a_before_b" else "←"
        causal_html += (
            f'<div class="pair causal">'
            f'<span class="fragment-id">Fragment {p["frag_a_id"]}</span> '
            f'<span class="clock">{p["clock_a"]}</span> '
            f'<span class="relation causal">{arrow}</span> '
            f'<span class="fragment-id">Fragment {p["frag_b_id"]}</span> '
            f'<span class="clock">{p["clock_b"]}</span>'
            f'</div>'
        )
    equal_html = ""
    for p in analysis["equal_pairs"]:
        equal_html += (
            f'<div class="pair equal">'
            f'<span class="fragment-id">Fragment {p["frag_a_id"]}</span> '
            f'<span class="relation equal">=</span> '
            f'<span class="fragment-id">Fragment {p["frag_b_id"]}</span> '
            f'<span class="clock">{p["clock_a"]}</span>'
            f'</div>'
        )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Demo Conflict Analysis - {doc_id}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 2rem; background: #f5f7fa; }}
            h1 {{ color: #1976d2; margin-bottom: 0.5rem; }}
            h2 {{ color: #424242; margin-bottom: 1rem; }}
            h3 {{ margin-top: 2rem; margin-bottom: 1rem; }}
            .conflict {{ color: #d32f2f; }}
            .causal {{ color: #388e3c; }}
            .equal {{ color: #757575; }}
            .pair {{ margin: 0.75rem 0; padding: 1rem; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 1rem; }}
            .pair.conflict {{ border-left: 5px solid #d32f2f; }}
            .pair.causal {{ border-left: 5px solid #388e3c; }}
            .pair.equal {{ border-left: 5px solid #9e9e9e; }}
            .clock {{ font-family: 'Consolas', monospace; background: #e3f2fd; padding: 4px 10px; border-radius: 4px; font-size: 0.9em; color: #1565c0; }}
            .fragment-id {{ font-weight: bold; color: #424242; }}
            .relation {{ font-weight: bold; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; text-transform: uppercase; }}
            .relation.concurrent {{ background: #ffebee; color: #d32f2f; }}
            .relation.causal {{ background: #e8f5e9; color: #388e3c; }}
            .relation.equal {{ background: #f5f5f5; color: #757575; }}
            a {{ color: #1976d2; text-decoration: none; margin-right: 1.5rem; padding: 0.5rem 1rem; background: white; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: all 0.2s; }}
            a:hover {{ background: #e3f2fd; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }}
            hr {{ margin: 2rem 0; border: none; border-top: 2px solid #e0e0e0; }}
            .nav {{ margin-bottom: 2rem; display: flex; gap: 0.5rem; }}
            .summary {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 1rem; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0; }}
            .stat-card {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
            .stat-number {{ font-size: 2.5rem; font-weight: bold; margin: 0.5rem 0; }}
            .stat-label {{ color: #757575; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; }}
            .stat-conflict .stat-number {{ color: #d32f2f; }}
            .stat-causal .stat-number {{ color: #388e3c; }}
            .stat-equal .stat-number {{ color: #757575; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/docs">📚 API Docs</a>
            <a href="/fragments/{doc_id}/analysis">📊 JSON Analysis</a>
            <a href="/">🏠 Home</a>
        </div>
        <h1>📄 Document: <em>{doc_id}</em></h1>
        
        <div class="stats">
            <div class="stat-card stat-conflict">
                <div class="stat-label">Concurrent Conflicts</div>
                <div class="stat-number">{len(analysis['concurrent_pairs'])}</div>
            </div>
            <div class="stat-card stat-causal">
                <div class="stat-label">Causal Updates</div>
                <div class="stat-number">{len(analysis['causal_pairs'])}</div>
            </div>
            <div class="stat-card stat-equal">
                <div class="stat-label">Equal Versions</div>
                <div class="stat-number">{len(analysis['equal_pairs'])}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Fragments</div>
                <div class="stat-number">{analysis['total_fragments']}</div>
            </div>
        </div>

        <h3 class="conflict">⚠️ Concurrent (Conflict) Pairs</h3>
        {concurrent_html if concurrent_html else '<p style="color: #757575; font-style: italic;">No conflicts found. All updates are causally related.</p>'}

        <h3 class="causal">✅ Causal (Safe) Pairs</h3>
        {causal_html if causal_html else '<p style="color: #757575; font-style: italic;">No causal pairs found.</p>'}

        <h3 class="equal">🟰 Equal (Identical) Pairs</h3>
        {equal_html if equal_html else '<p style="color: #757575; font-style: italic;">No duplicate versions found.</p>'}

        <div class="summary">
            <strong>📋 Summary:</strong> {analysis['summary']}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)