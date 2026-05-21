from vector_clock import VectorClock

NODES = ["S1", "S2", "S3"]

def test_initial_clock():
    vc = VectorClock(NODES)
    assert vc.clocks == {"S1": 0, "S2": 0, "S3": 0}

def test_increment():
    vc = VectorClock(NODES)
    vc2 = vc.increment("S1")
    assert vc2.clocks["S1"] == 1
    # Bản gốc không đổi
    assert vc.clocks["S1"] == 0

def test_merge():
    v1 = VectorClock(NODES, {"S1": 1, "S2": 0, "S3": 0})
    v2 = VectorClock(NODES, {"S1": 0, "S2": 2, "S3": 1})
    merged = v1.merge(v2)
    assert merged.clocks == {"S1": 1, "S2": 2, "S3": 1}

def test_happens_before_true():
    v1 = VectorClock(NODES, {"S1": 1, "S2": 0, "S3": 0})
    v2 = VectorClock(NODES, {"S1": 2, "S2": 1, "S3": 0})
    assert v1.happens_before(v2) == True
    assert v2.happens_before(v1) == False

def test_concurrent():
    v1 = VectorClock(NODES, {"S1": 1, "S2": 0, "S3": 0})
    v2 = VectorClock(NODES, {"S1": 0, "S2": 1, "S3": 0})
    assert v1.is_concurrent(v2) == True

def test_same_clock_not_concurrent():
    v1 = VectorClock(NODES, {"S1": 2, "S2": 1, "S3": 0})
    v2 = VectorClock(NODES, {"S1": 2, "S2": 1, "S3": 0})
    assert v1.is_concurrent(v2) == False