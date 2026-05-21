from typing import Dict, List

class VectorClock:
    def __init__(self, nodes: List[str], initial: Dict[str, int] = None):
        """
        Khởi tạo vector clock cho danh sách các node (site).
        Nếu initial được truyền, nó sẽ gán giá trị tương ứng (missing node -> 0).
        """
        self.nodes = sorted(nodes)  # Đảm bảo thứ tự nhất quán
        if initial:
            self.clocks = {n: initial.get(n, 0) for n in self.nodes}
        else:
            self.clocks = {n: 0 for n in self.nodes}

    def increment(self, node_id: str) -> 'VectorClock':
        """
        Tạo bản sao mới của VectorClock, tăng counter của node_id thêm 1.
        Không thay đổi đối tượng gốc (immutable pattern).
        """
        new_clocks = self.clocks.copy()
        new_clocks[node_id] += 1
        return VectorClock(self.nodes, new_clocks)

    def merge(self, other: 'VectorClock') -> 'VectorClock':
        """
        Hợp nhất với clock khác: lấy max của từng node.
        Trả về VectorClock mới.
        """
        merged = {}
        for n in self.nodes:
            merged[n] = max(self.clocks[n], other.clocks.get(n, 0))
        return VectorClock(self.nodes, merged)

    def happens_before(self, other: 'VectorClock') -> bool:
        """
        Kiểm tra self có strictly xảy ra trước other không.
        Điều kiện: self[n] <= other[n] với mọi n, và tồn tại ít nhất 1 n có self[n] < other[n].
        """
        any_strict = False
        for n in self.nodes:
            if self.clocks[n] > other.clocks.get(n, 0):
                return False
            if self.clocks[n] < other.clocks.get(n, 0):
                any_strict = True
        return any_strict

    def is_concurrent(self, other: 'VectorClock') -> bool:
        """
        Hai clock là đồng thời nếu không cái nào happens_before cái kia.
        Ngoại lệ: nếu hai clock bằng nhau thì coi là cùng phiên bản -> không concurrent.
        """
        if self.clocks == other.clocks:
            return False
        return not self.happens_before(other) and not other.happens_before(self)

    def to_dict(self) -> Dict[str, int]:
        """Trả về dictionary để lưu DB."""
        return self.clocks.copy()

    @classmethod
    def from_dict(cls, nodes: List[str], d: Dict[str, int]) -> 'VectorClock':
        """Khởi tạo VectorClock từ dict (ví dụ từ DB)."""
        return cls(nodes, d)

    def __repr__(self):
        return f"VectorClock({self.clocks})"