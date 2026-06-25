"""
Map module — Bản đồ lưới AMR
Cải tiến so với bản gốc:
  - Tùy chỉnh kích thước lưới
  - random_map() kiểm tra tính liên thông (BFS) đảm bảo luôn có đường đi
  - Hỗ trợ thêm/xóa vật cản động
"""

from random import random
from collections import deque


class Maps(object):

    def __init__(self, rows=20, cols=30):
        self.rows = rows
        self.cols = cols
        self.map = []
        self._init_map()

    def _init_map(self):
        """Khởi tạo lưới với viền là tường (=1), bên trong trống (=0)."""
        self.map = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                is_border = (r == 0 or r == self.rows - 1 or
                             c == 0 or c == self.cols - 1)
                row.append(1 if is_border else 0)
            self.map.append(row)

    def random_map(self, obstacle_prob=0.2):
        """
        Tạo vật cản ngẫu nhiên, đảm bảo tính liên thông toàn bộ ô trống.
        obstacle_prob: xác suất mỗi ô bên trong trở thành vật cản (mặc định 20%).
        """
        MAX_TRIES = 20
        for _ in range(MAX_TRIES):
            self._init_map()
            for r in range(1, self.rows - 1):
                for c in range(1, self.cols - 1):
                    if random() < obstacle_prob:
                        self.map[r][c] = 1
            if self._is_connected():
                return
        # Fallback: bản đồ trống
        self._init_map()

    def _is_connected(self):
        """Kiểm tra tất cả ô trống có liên thông không (BFS)."""
        start = None
        free_count = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.map[r][c] == 0:
                    free_count += 1
                    if start is None:
                        start = (r, c)
        if start is None:
            return False
        visited = set()
        queue = deque([start])
        visited.add(start)
        while queue:
            r, c = queue.popleft()
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if (0 <= nr < self.rows and 0 <= nc < self.cols
                        and self.map[nr][nc] == 0
                        and (nr, nc) not in visited):
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        return len(visited) == free_count

    def add_obstacle(self, row, col):
        if 1 <= row < self.rows-1 and 1 <= col < self.cols-1:
            self.map[row][col] = 1

    def remove_obstacle(self, row, col):
        if 1 <= row < self.rows-1 and 1 <= col < self.cols-1:
            self.map[row][col] = 0

    def toggle_obstacle(self, row, col):
        if 1 <= row < self.rows-1 and 1 <= col < self.cols-1:
            self.map[row][col] = 0 if self.map[row][col] else 1

    def is_free(self, row, col):
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.map[row][col] == 0
        return False
