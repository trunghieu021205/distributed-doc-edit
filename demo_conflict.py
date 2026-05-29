# demo_conflict.py
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def print_json(response):
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

def main():
    print("🚀 Starting conflict scenario simulation...\n")

    # 1. Create original fragment (S1)
    print("1. Creating original fragment (S1=1)...")
    payload = {
        "doc_id": "demo_doc",
        "content": "Dòng đầu tiên – phiên bản gốc",
        "node_id": "S1",
        "vector_clock": {"clock": {"S1": 1}}
    }
    r = requests.post(f"{BASE_URL}/fragments", json=payload)
    frag_original = r.json()
    print(f"   Fragment id={frag_original['id']} clock={frag_original['vector_clock']}\n")

    # 2. S1 edits that line (S1:2)
    print("2. S1 edits (increment clock -> S1:2)...")
    payload = {
        "doc_id": "demo_doc",
        "content": "Dòng đầu tiên – S1 sửa",
        "node_id": "S1",
        "vector_clock": {"clock": {"S1": 2}}
    }
    r = requests.post(f"{BASE_URL}/fragments", json=payload)
    frag_s1 = r.json()
    print(f"   Fragment id={frag_s1['id']} clock={frag_s1['vector_clock']}\n")

    # 3. S2 also edits that line, only knows original version (S1:1, S2:1)
    print("3. S2 edits same line, unaware of S1's change (S1:1, S2:1)...")
    payload = {
        "doc_id": "demo_doc",
        "content": "Dòng đầu tiên – S2 sửa",
        "node_id": "S2",
        "vector_clock": {"clock": {"S1": 1, "S2": 1}}
    }
    r = requests.post(f"{BASE_URL}/fragments", json=payload)
    frag_s2 = r.json()
    print(f"   Fragment id={frag_s2['id']} clock={frag_s2['vector_clock']}\n")

    # 4. Compare clocks of S1 and S2 (direct comparison)
    print("4. Comparing two vector clocks S1 vs S2...")
    compare_payload = {
        "clock_a": frag_s1["vector_clock"],
        "clock_b": frag_s2["vector_clock"]
    }
    r = requests.post(f"{BASE_URL}/fragments/compare", json=compare_payload)
    compare_result = r.json()
    print(f"   Result: {compare_result['relation']} – {compare_result['explanation']}\n")

    # 5. Analyze entire document
    print("5. Analyzing entire document...")
    r = requests.get(f"{BASE_URL}/fragments/demo_doc/analysis")
    analysis = r.json()
    print(f"   Total fragments: {analysis['total_fragments']}")
    print(f"   Number of conflict branches: {analysis['conflict_count']}")
    print("   Concurrent pairs:")
    for pair in analysis["concurrent_pairs"]:
        print(f"      - Fragment {pair['frag_a_id']} <-> {pair['frag_b_id']} : {pair['relation']}")
    print("   Causal pairs:")
    for pair in analysis["causal_pairs"]:
        print(f"      - Fragment {pair['frag_a_id']} -> {pair['frag_b_id']} : {pair['relation']}")
    print("\n✅ Simulation complete. You can view the demo interface at http://127.0.0.1:8000/demo/demo_doc")

if __name__ == "__main__":
    main()