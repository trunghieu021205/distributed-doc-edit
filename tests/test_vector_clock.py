import pytest
from vector_clock import VectorClock

class TestVectorClock:
    def test_increment(self):
        vc = VectorClock({"S1": 1})
        vc.increment("S1")
        assert vc.clock == {"S1": 2}
        vc.increment("S2")
        assert vc.clock == {"S1": 2, "S2": 1}

    def test_merge(self):
        vc1 = VectorClock({"S1": 1, "S2": 2})
        vc2 = VectorClock({"S1": 2, "S3": 1})
        vc1.merge(vc2)
        assert vc1.clock == {"S1": 2, "S2": 2, "S3": 1}

    def test_happens_before_true(self):
        vc1 = VectorClock({"S1": 1, "S2": 1})
        vc2 = VectorClock({"S1": 1, "S2": 2})
        assert vc1.happens_before(vc2)

    def test_happens_before_false_equal(self):
        vc1 = VectorClock({"S1": 1})
        vc2 = VectorClock({"S1": 1})
        assert not vc1.happens_before(vc2)

    def test_is_concurrent_true(self):
        vc1 = VectorClock({"S1": 1, "S2": 2})
        vc2 = VectorClock({"S1": 2, "S2": 1})
        assert vc1.is_concurrent(vc2)

    def test_is_concurrent_false_equal(self):
        vc1 = VectorClock({"S1": 1})
        vc2 = VectorClock({"S1": 1})
        assert not vc1.is_concurrent(vc2)

    def test_from_dict_and_to_dict(self):
        d = {"A": 3, "B": 5}
        vc = VectorClock.from_dict(d)
        assert vc.to_dict() == d