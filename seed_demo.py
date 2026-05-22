import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

doc_id = "demo_doc"
fragments = [
    {
        "doc_id": doc_id,
        "content": "Dòng đầu tiên – phiên bản gốc",
        "node_id": "S1",
        "vector_clock": {"clock": {"S1": 1}}
    },
    {
        "doc_id": doc_id,
        "content": "Dòng đầu tiên – S1 sửa",
        "node_id": "S1",
        "vector_clock": {"clock": {"S1": 2}}
    },
    {
        "doc_id": doc_id,
        "content": "Dòng đầu tiên – S2 sửa (không biết S1)",
        "node_id": "S2",
        "vector_clock": {"clock": {"S1": 1, "S2": 1}}
    },
    {
        "doc_id": doc_id,
        "content": "Dòng đầu tiên – S3 sửa sau khi biết S1",
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
            print(f"✔ Đã tạo fragment {i}: id={result['id']} clock={result['vector_clock']}")
        else:
            print(f"✘ Lỗi khi tạo fragment {i} (code {code}): {result}")

    print(f"\n✅ Seed hoàn tất. Truy cập http://127.0.0.1:8000/docs để kiểm tra, hoặc http://127.0.0.1:8000/demo/{doc_id} để xem giao diện demo.")

if __name__ == "__main__":
    main()