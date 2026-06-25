"""
core/map_editor.py — Map Editor
Vẽ tường bằng cách kéo chuột, lưu/tải bản đồ JSON.

Phím tắt:
  E          : Bật/tắt chế độ edit
  Kéo trái  : Vẽ tường
  Kéo phải  : Xóa tường
  Ctrl+S     : Lưu bản đồ
  Ctrl+L     : Mở panel tải bản đồ
  0-9        : Chọn bản đồ từ danh sách (khi panel mở)
"""

import json
import os
import time

from utils.utils import turn2node

MAPS_DIR = "maps"

# Bản đồ mẫu sẵn có
PRESET_MAPS = {
    "maze_10x10": {
        "name": "Maze 10x10",
        "rows": 12, "cols": 12, "cell_mm": 200,
        "data": None,  # Sẽ tạo procedural
    },
    "office": {
        "name": "Office Layout",
        "rows": 14, "cols": 20, "cell_mm": 200,
        "data": None,
    },
    "warehouse": {
        "name": "Warehouse",
        "rows": 16, "cols": 24, "cell_mm": 200,
        "data": None,
    },
}


class MapEditor:

    MODE_DRAW  = "DRAW"
    MODE_ERASE = "ERASE"

    def __init__(self):
        self.active       = False
        self.mode         = self.MODE_DRAW
        self.dragging     = False
        self.last_node    = None
        self.show_panel   = False   # Panel load bản đồ
        self.panel_maps   = []      # Danh sách file trong maps/
        self.map_changed  = False   # Đánh dấu có thay đổi chưa lưu
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(MAPS_DIR, exist_ok=True)

    def toggle(self):
        self.active   = not self.active
        self.dragging = False
        if not self.active:
            self.show_panel = False

    def toggle_panel(self):
        """Mở/đóng panel danh sách bản đồ."""
        self.show_panel = not self.show_panel
        if self.show_panel:
            self.panel_maps = self._list_maps()

    # ── Xử lý mouse ─────────────────────────────

    def on_mouse_down(self, btn, pos, map_obj, W, H) -> bool:
        """Trả về True nếu đã xử lý (không để sự kiện lan ra ngoài)."""
        if not self.active:
            return False

        node = turn2node(map_obj.map, W, H, pos[0], pos[1])
        if btn == 1:
            self.mode     = self.MODE_DRAW
            self.dragging = True
            self._apply(map_obj, node, wall=True)
        elif btn == 3:
            self.mode     = self.MODE_ERASE
            self.dragging = True
            self._apply(map_obj, node, wall=False)

        self.last_node  = node
        self.map_changed= True
        return True

    def on_mouse_motion(self, pos, map_obj, W, H):
        if not self.active or not self.dragging:
            return
        node = turn2node(map_obj.map, W, H, pos[0], pos[1])
        if node != self.last_node:
            self._apply(map_obj, node, wall=(self.mode == self.MODE_DRAW))
            self.last_node   = node
            self.map_changed = True

    def on_mouse_up(self):
        self.dragging = False

    def _apply(self, map_obj, node, wall: bool):
        r, c = node
        # Không vẽ lên viền
        if 1 <= r < map_obj.rows - 1 and 1 <= c < map_obj.cols - 1:
            map_obj.map[r][c] = 1 if wall else 0

    # ── Lưu / Tải ───────────────────────────────

    def save(self, map_obj, cell_mm: int, name: str = None) -> str:
        if name is None:
            name = f"map_{int(time.time())}"
        # Loại bỏ ký tự đặc biệt
        safe = "".join(c for c in name if c.isalnum() or c in '_-')
        if not safe:
            safe = f"map_{int(time.time())}"

        payload = {
            "name":    safe,
            "rows":    map_obj.rows,
            "cols":    map_obj.cols,
            "cell_mm": cell_mm,
            "data":    [list(row) for row in map_obj.map],
        }
        path = os.path.join(MAPS_DIR, f"{safe}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        self.map_changed = False
        print(f"[MapEditor] Đã lưu: {path}")
        return path

    def load(self, filename: str) -> dict:
        """Trả về dict {name, rows, cols, cell_mm, data} hoặc None."""
        path = os.path.join(MAPS_DIR, filename)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.map_changed = False
            print(f"[MapEditor] Đã tải: {path}")
            return data
        except Exception as e:
            print(f"[MapEditor] Lỗi tải {path}: {e}")
            return None

    def _list_maps(self) -> list:
        self._ensure_dir()
        files = sorted(
            f for f in os.listdir(MAPS_DIR) if f.endswith(".json")
        )
        return files

    # ── Bản đồ mẫu ──────────────────────────────

    @staticmethod
    def make_maze(rows=12, cols=12, cell_mm=200) -> dict:
        """Tạo mê cung đơn giản."""
        data = []
        for r in range(rows):
            row = []
            for c in range(cols):
                border = (r == 0 or r == rows-1
                          or c == 0 or c == cols-1)
                # Tường nội bộ
                inner = (r % 3 == 0 and c % 4 != 1) and not border
                row.append(1 if (border or inner) else 0)
            data.append(row)
        # Đảm bảo ô góc trong luôn trống
        for r in range(1, rows-1):
            for c in range(1, cols-1):
                if data[r][c] == 1:
                    # Kiểm tra còn lối đi không
                    free_neighbors = sum(
                        data[r+dr][c+dc] == 0
                        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
                        if 0 <= r+dr < rows and 0 <= c+dc < cols
                    )
                    if free_neighbors == 0:
                        data[r][c] = 0
        return {"name": "Maze", "rows": rows, "cols": cols,
                "cell_mm": cell_mm, "data": data}

    @staticmethod
    def make_office(rows=14, cols=20, cell_mm=200) -> dict:
        """Layout văn phòng với phòng và hành lang."""
        data = [[1 if (r==0 or r==rows-1 or c==0 or c==cols-1)
                 else 0 for c in range(cols)] for r in range(rows)]
        # Tường phòng
        walls = [
            # Phòng trái
            [(r, 7) for r in range(1, 9)],
            [(4, c) for c in range(1, 7)],
            # Phòng phải
            [(r, 13) for r in range(1, 9)],
            [(4, c) for c in range(14, 19)],
            # Phòng dưới
            [(9, c) for c in range(1, 7)],
            [(9, c) for c in range(13, 19)],
        ]
        for wall_group in walls:
            for r, c in wall_group:
                if 0 < r < rows-1 and 0 < c < cols-1:
                    data[r][c] = 1
        # Tạo cửa (khoảng trống trong tường)
        doors = [(6, 7), (2, 7), (6, 13), (2, 13), (9, 4), (9, 16)]
        for r, c in doors:
            if 0 < r < rows-1 and 0 < c < cols-1:
                data[r][c] = 0
        return {"name": "Office", "rows": rows, "cols": cols,
                "cell_mm": cell_mm, "data": data}

    @staticmethod
    def make_warehouse(rows=16, cols=24, cell_mm=200) -> dict:
        """Kho hàng với các hàng kệ."""
        data = [[1 if (r==0 or r==rows-1 or c==0 or c==cols-1)
                 else 0 for c in range(cols)] for r in range(rows)]
        # Kệ hàng (4 hàng kệ, mỗi kệ dài 8 ô)
        shelf_starts_r = [2, 6, 10, 14]
        shelf_starts_c = [2, 12]
        for sr in [2, 5, 9, 12]:
            for sc in [2, 10, 18]:
                for dc in range(6):
                    r, c = sr, sc + dc
                    if 0 < r < rows-1 and 0 < c < cols-1:
                        data[r][c] = 1
        return {"name": "Warehouse", "rows": rows, "cols": cols,
                "cell_mm": cell_mm, "data": data}
