# demo_conflict.py
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def print_json(response):
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

def main():
    print("🚀 Bắt đầu mô phỏng kịch bản conflict...\n")

    # 1. Tạo fragment gốc (S1)
    print("1. Tạo fragment gốc (S1=1)...")
    payload = {
        "doc_id": "demo_doc",
        "content": "Dòng đầu tiên – phiên bản gốc",
        "node_id": "S1",
        "vector_clock": {"clock": {"S1": 1}}
    }
    r = requests.post(f"{BASE_URL}/fragments", json=payload)
    frag_original = r.json()
    print(f"   Fragment id={frag_original['id']} clock={frag_original['vector_clock']}\n")

    # 2. S1 sửa dòng đó (S1:2)
    print("2. S1 chỉnh sửa (tăng clock -> S1:2)...")
    payload = {
        "doc_id": "demo_doc",
        "content": "Dòng đầu tiên – S1 sửa",
        "node_id": "S1",
        "vector_clock": {"clock": {"S1": 2}}
    }
    r = requests.post(f"{BASE_URL}/fragments", json=payload)
    frag_s1 = r.json()
    print(f"   Fragment id={frag_s1['id']} clock={frag_s1['vector_clock']}\n")

    # 3. S2 cũng sửa dòng đó, chỉ biết phiên bản gốc (S1:1, S2:1)
    print("3. S2 chỉnh sửa cùng dòng, không biết về thay đổi của S1 (S1:1, S2:1)...")
    payload = {
        "doc_id": "demo_doc",
        "content": "Dòng đầu tiên – S2 sửa",
        "node_id": "S2",
        "vector_clock": {"clock": {"S1": 1, "S2": 1}}
    }
    r = requests.post(f"{BASE_URL}/fragments", json=payload)
    frag_s2 = r.json()
    print(f"   Fragment id={frag_s2['id']} clock={frag_s2['vector_clock']}\n")

    # 4. So sánh clock của S1 và S2 (so sánh trực tiếp)
    print("4. So sánh hai vector clock S1 vs S2...")
    compare_payload = {
        "clock_a": frag_s1["vector_clock"],
        "clock_b": frag_s2["vector_clock"]
    }
    r = requests.post(f"{BASE_URL}/fragments/compare", json=compare_payload)
    compare_result = r.json()
    print(f"   Kết quả: {compare_result['relation']} – {compare_result['explanation']}\n")

    # 5. Phân tích toàn bộ document
    print("5. Phân tích toàn bộ document...")
    r = requests.get(f"{BASE_URL}/fragments/demo_doc/analysis")
    analysis = r.json()
    print(f"   Tổng fragment: {analysis['total_fragments']}")
    print(f"   Số conflict branch: {analysis['conflict_count']}")
    print("   Các cặp concurrent:")
    for pair in analysis["concurrent_pairs"]:
        print(f"      - Fragment {pair['frag_a_id']} <-> {pair['frag_b_id']} : {pair['relation']}")
    print("   Các cặp causal:")
    for pair in analysis["causal_pairs"]:
        print(f"      - Fragment {pair['frag_a_id']} -> {pair['frag_b_id']} : {pair['relation']}")
    print("\n✅ Hoàn thành mô phỏng. Bạn có thể xem giao diện demo tại http://127.0.0.1:8000/demo/demo_doc")

if __name__ == "__main__":
    main()