# tests/test_api.py
import pytest


def test_create_fragment(client):
    resp = client.post("/fragments", json={
        "doc_id": "doc1", "content": "Hello", "node_id": "A"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_id"] == "doc1"
    assert data["content"] == "Hello"
    assert data["vector_clock"] == {"A": 1}


def test_get_fragments(client):
    client.post("/fragments", json={"doc_id": "docX", "content": "F1", "node_id": "A"})
    client.post("/fragments", json={"doc_id": "docX", "content": "F2", "node_id": "B"})
    resp = client.get("/fragments/docX")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_fragment_success(client):
    create_resp = client.post("/fragments", json={
        "doc_id": "doc1", "content": "Original", "node_id": "A",
        "vector_clock": {"clock": {"A": 1}}
    })
    assert create_resp.status_code == 201
    frag_id = create_resp.json()["id"]

    update_resp = client.put(f"/fragments/{frag_id}", json={
        "content": "Updated",
        "node_id": "B",
        "vector_clock": {"A": 1}
    })
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["content"] == "Updated"
    assert data["vector_clock"] == {"A": 1, "B": 1}


def test_update_fragment_conflict(client):
    create_resp = client.post("/fragments", json={
        "doc_id": "doc1", "content": "Original", "node_id": "A",
        "vector_clock": {"clock": {"A": 2}}
    })
    assert create_resp.status_code == 201
    frag_id = create_resp.json()["id"]

    resp = client.put(f"/fragments/{frag_id}", json={
        "content": "Conflict Update",
        "node_id": "C",
        "vector_clock": {"A": 1}   # cũ hơn → conflict
    })
    assert resp.status_code == 409
    assert "conflict" in resp.json()["detail"].lower()


def test_update_fragment_not_found(client):
    resp = client.put("/fragments/999", json={
        "content": "x", "node_id": "A", "vector_clock": {"A": 1}
    })
    assert resp.status_code == 404


def test_get_fragments_empty(client):
    resp = client.get("/fragments/nonexistent_doc")
    assert resp.status_code == 200
    assert resp.json() == []