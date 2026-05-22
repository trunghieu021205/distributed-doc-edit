import copy
from typing import Dict

class VectorClock:
    def __init__(self, clock: Dict[str, int] = None):
        self.clock = clock if clock is not None else {}

    def increment(self, node_id: str) -> None:
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def merge(self, other: 'VectorClock') -> None:
        for node, counter in other.clock.items():
            if self.clock.get(node, 0) < counter:
                self.clock[node] = counter

    def happens_before(self, other: 'VectorClock') -> bool:
        at_least_one_strictly_less = False
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        for n in all_nodes:
            self_val = self.clock.get(n, 0)
            other_val = other.clock.get(n, 0)
            if self_val > other_val:
                return False
            if self_val < other_val:
                at_least_one_strictly_less = True
        return at_least_one_strictly_less

    def is_concurrent(self, other: 'VectorClock') -> bool:
        if self.clock == other.clock:
            return False
        return not self.happens_before(other) and not other.happens_before(self)

    def to_dict(self) -> Dict[str, int]:
        return copy.deepcopy(self.clock)

    @classmethod
    def from_dict(cls, d: Dict[str, int]) -> 'VectorClock':
        return cls(clock=copy.deepcopy(d))

    def __repr__(self):
        return f"VectorClock({self.clock})"