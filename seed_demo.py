import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

doc_id = "demo_doc"
fragments = [
    {
        "doc_id": doc_id,
        "content": "First line – original version",
        "node_id": "S1",
        "vector_clock": {"clock": {"S1": 1}}
    },
    {
        "doc_id": doc_id,
        "content": "First line – S1 edit",
        "node_id": "S1",
        "vector_clock": {"clock": {"S1": 2}}
    },
    {
        "doc_id": doc_id,
        "content": "First line – S2 edit (unaware of S1)",
        "node_id": "S2",
        "vector_clock": {"clock": {"S1": 1, "S2": 1}}
    },
    {
        "doc_id": doc_id,
        "content": "First line – S3 edit after knowing S1",
        "node_id": "S3",
        "vector_clock": {"clock": {"S1": 2, "S3": 1}}
    }
]

def post_fragment(data):
    url = f"{BASE_URL}/fragments"
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8')), resp.status
    except urllib.error.HTTPError as e:
        return e.read().decode(), e.code

def main():
    for i, frag in enumerate(fragments, 1):
        result, code = post_fragment(frag)
        if code == 201:
            print(f"✔ Created fragment {i}: id={result['id']} clock={result['vector_clock']}")
        else:
            print(f"✘ Error creating fragment {i} (code {code}): {result}")

    print(f"\n✅ Seed complete. Visit http://127.0.0.1:8000/docs to check, or http://127.0.0.1:8000/demo/{doc_id} to view demo interface.")

if __name__ == "__main__":
    main()