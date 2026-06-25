"""
core/waypoint_manager.py — Multi-Waypoint Navigation
AMR tự động đi qua nhiều điểm đích theo thứ tự.

Sử dụng:
  W               : Bật/tắt chế độ waypoint
  Ctrl+Click phải : Thêm waypoint vào hàng đợi
  SPACE           : Bắt đầu tìm đường đến waypoint đầu tiên
  Backspace       : Xóa waypoint cuối cùng
  Ctrl+R          : Xóa tất cả waypoint
"""


class WaypointManager:

    MAX_WP = 10

    def __init__(self):
        self.active    = False
        self.waypoints = []    # List (row, col)
        self.current   = 0     # Index điểm đích hiện tại
        self.loop_mode = False # Lặp lại khi xong tất cả

    # ── Trạng thái ───────────────────────────────

    def toggle(self):
        self.active = not self.active
        if not self.active:
            self.clear()

    def toggle_loop(self):
        self.loop_mode = not self.loop_mode

    # ── Quản lý waypoints ────────────────────────

    def add(self, node: tuple) -> bool:
        if len(self.waypoints) >= self.MAX_WP:
            return False
        if node not in self.waypoints:
            self.waypoints.append(node)
            return True
        return False

    def remove_last(self):
        if self.waypoints:
            self.waypoints.pop()
            if self.current >= len(self.waypoints):
                self.current = max(0, len(self.waypoints) - 1)

    def clear(self):
        self.waypoints = []
        self.current   = 0

    # ── Navigation ───────────────────────────────

    def current_goal(self):
        """Trả về node đích hiện tại."""
        if self.active and self.current < len(self.waypoints):
            return self.waypoints[self.current]
        return None

    def advance(self) -> bool:
        """
        Chuyển sang waypoint tiếp theo.
        Trả về True nếu còn waypoint tiếp theo.
        """
        self.current += 1
        if self.current >= len(self.waypoints):
            if self.loop_mode and self.waypoints:
                self.current = 0
                return True
            return False
        return True

    def is_done(self) -> bool:
        if not self.active or not self.waypoints:
            return True
        return self.current >= len(self.waypoints) and not self.loop_mode

    def reset_progress(self):
        """Quay về waypoint đầu."""
        self.current = 0

    # ── Thông tin ────────────────────────────────

    def remaining(self) -> list:
        return self.waypoints[self.current:]

    def completed(self) -> list:
        return self.waypoints[:self.current]

    def progress_text(self) -> str:
        if not self.waypoints:
            return "0/0"
        return f"{min(self.current, len(self.waypoints))}/{len(self.waypoints)}"

    def __len__(self):
        return len(self.waypoints)
