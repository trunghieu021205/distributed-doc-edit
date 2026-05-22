# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json

from database import get_db
import crud, schemas
from vector_clock import VectorClock

app = FastAPI(
    title="Document Fragment Sync API",
    description="Hệ thống theo dõi cập nhật tài liệu phân tán sử dụng Vector Clock, phát hiện conflict.",
    version="1.0.0",
)

# ---------------------------- Utility function ----------------------------

def analyze_fragments(fragments: List[Any]) -> Dict[str, Any]:
    """
    Phân tích danh sách fragment, trả về các cặp concurrent, causal, equal và tổng số conflict.
    Có thể dùng cho cả endpoint phân tích và trang demo.
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
          tags=["Fragments"], summary="Tạo fragment mới")
def create_fragment(payload: schemas.FragmentCreate, db: Session = Depends(get_db)):
    """
    Tạo một fragment văn bản với vector clock.  
    Nếu không cung cấp vector_clock, hệ thống sẽ tự tạo clock mặc định {node_id: 1}.
    """
    fragment = crud.create_fragment(db, payload)
    return fragment


@app.get("/fragments/{doc_id}", response_model=List[schemas.FragmentResponse],
         tags=["Fragments"], summary="Lấy tất cả fragment của một document")
def get_fragments(doc_id: str, db: Session = Depends(get_db)):
    """Trả về danh sách fragment thuộc về document có `doc_id` cho trước."""
    return crud.get_fragments_by_doc_id(db, doc_id)


@app.put("/fragments/{frag_id}", response_model=schemas.FragmentResponse,
         tags=["Fragments"], summary="Cập nhật fragment")
def update_fragment(frag_id: int, payload: schemas.FragmentUpdate, db: Session = Depends(get_db)):
    """
    Cập nhật nội dung và vector clock của một fragment.  
    Sử dụng để đồng bộ thay đổi từ các site.
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
          tags=["Analysis"], summary="So sánh hai vector clock")
def compare_clocks(payload: schemas.CompareRequest):
    """
    **Metric chính của đề tài**: Phân loại quan hệ nhân quả giữa hai vector clock.

    - `concurrent`  → Hai update song song, tạo ra Branch/Conflict.
    - `a_before_b`  → A xảy ra trước B (causal).
    - `b_before_a`  → B xảy ra trước A (causal).
    - `equal`       → Hai clock giống hệt nhau.
    """
    vc_a = VectorClock.from_dict(payload.clock_a)
    vc_b = VectorClock.from_dict(payload.clock_b)

    if payload.clock_a == payload.clock_b:
        relation = "equal"
        is_concurrent = False
        explanation = "Hai vector clock giống hệt nhau – cùng một phiên bản."
    elif vc_a.happens_before(vc_b):
        relation = "a_before_b"
        is_concurrent = False
        explanation = "A → B: A là nguyên nhân của B. B đã biết về A → Causal Update, không conflict."
    elif vc_b.happens_before(vc_a):
        relation = "b_before_a"
        is_concurrent = False
        explanation = "B → A: B là nguyên nhân của A. A đã biết về B → Causal Update, không conflict."
    else:
        relation = "concurrent"
        is_concurrent = True
        explanation = "A ∥ B: Hai update độc lập, không biết nhau → Concurrent Update → Conflict."

    return schemas.CompareResponse(
        clock_a=payload.clock_a,
        clock_b=payload.clock_b,
        relation=relation,
        is_concurrent=is_concurrent,
        explanation=explanation,
    )


@app.get("/fragments/{doc_id}/analysis", response_model=schemas.DocumentAnalysis,
         tags=["Analysis"], summary="Phân tích toàn bộ document")
def analyze_document(doc_id: str, db: Session = Depends(get_db)):
    """
    Quét tất cả fragment của một document, xác định các cặp có quan hệ:
    - **Concurrent** (xung đột) – cần hòa giải.
    - **Causal** (có trước – có sau) – không xung đột.
    - **Equal** (giống hệt).

    Trả về báo cáo tóm tắt.
    """
    fragments = crud.get_fragments_by_doc_id(db, doc_id)
    if not fragments:
        raise HTTPException(status_code=404, detail=f"No fragments found for doc '{doc_id}'")

    analysis = analyze_fragments(fragments)
    return schemas.DocumentAnalysis(**analysis)


# ---------------------------- Demo UI ----------------------------

@app.get("/demo/{doc_id}", response_class=HTMLResponse,
         tags=["Demo"], summary="Giao diện demo trực quan")
def demo_page(doc_id: str, db: Session = Depends(get_db)):
    """
    Trang web đơn giản hiển thị kết quả phân tích conflict của một document.
    Dùng để thuyết trình hoặc kiểm tra nhanh.
    """
    fragments = crud.get_fragments_by_doc_id(db, doc_id)
    if not fragments:
        return HTMLResponse(content=f"<h2>Document '{doc_id}' không tồn tại.</h2>", status_code=404)

    analysis = analyze_fragments(fragments)
    # Tạo HTML
    concurrent_html = ""
    for p in analysis["concurrent_pairs"]:
        concurrent_html += (
            f'<div class="pair">'
            f'Fragment {p["frag_a_id"]} <span class="clock">{p["clock_a"]}</span> '
            f'↔ Fragment {p["frag_b_id"]} <span class="clock">{p["clock_b"]}</span>'
            f'</div>'
        )
    causal_html = ""
    for p in analysis["causal_pairs"]:
        arrow = "→" if p["relation"] == "a_before_b" else "←"
        causal_html += (
            f'<div class="pair">'
            f'Fragment {p["frag_a_id"]} <span class="clock">{p["clock_a"]}</span> '
            f'{arrow} Fragment {p["frag_b_id"]} <span class="clock">{p["clock_b"]}</span>'
            f'</div>'
        )
    equal_html = ""
    for p in analysis["equal_pairs"]:
        equal_html += (
            f'<div class="pair">'
            f'Fragment {p["frag_a_id"]} = Fragment {p["frag_b_id"]} '
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
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 2rem; background: #fafafa; }}
            h1 {{ color: #1565c0; }}
            h2 {{ color: #333; }}
            .conflict {{ color: #d32f2f; font-weight: bold; }}
            .causal  {{ color: #2e7d32; }}
            .pair {{ margin: 0.5rem 0; padding: 0.75rem; background: white; border-left: 4px solid #2196f3; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .clock {{ font-family: monospace; background: #e3f2fd; padding: 2px 6px; border-radius: 3px; }}
            a {{ color: #1565c0; text-decoration: none; margin-right: 1rem; }}
            a:hover {{ text-decoration: underline; }}
            hr {{ margin: 2rem 0; }}
            .nav {{ margin-bottom: 2rem; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/docs">📚 Swagger UI</a>
            <a href="/fragments/{doc_id}/analysis">📊 JSON Analysis</a>
            <a href="/">🏠 Home</a>
        </div>
        <h1>📄 Document: <em>{doc_id}</em></h1>
        <h2>Tổng số fragment: {analysis['total_fragments']}</h2>

        <h3 class="conflict">⚠️ Concurrent (Conflict): {len(analysis['concurrent_pairs'])} cặp</h3>
        {concurrent_html if concurrent_html else '<p>Không có xung đột nào.</p>'}

        <h3 class="causal">✅ Causal (An toàn): {len(analysis['causal_pairs'])} cặp</h3>
        {causal_html if causal_html else '<p>Không có cặp causal nào.</p>'}

        <h3>🟰 Equal (Giống hệt): {len(analysis['equal_pairs'])} cặp</h3>
        {equal_html if equal_html else '<p>Không có cặp trùng lặp.</p>'}

        <hr>
        <p><strong>Tóm tắt:</strong> {analysis['summary']}</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)