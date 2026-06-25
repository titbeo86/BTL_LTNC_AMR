"""
Sensor module — Cảm biến AMR
Mỗi chu kỳ trả về:
  - valid_dirs: tập hợp hướng hợp lệ (0/90/180/270) quanh vị trí hiện tại
  - Làm việc hoàn toàn trên tọa độ NODE, không lẫn pixel
"""

from utils.utils import turn2node


class Sensors(object):

    # Ánh xạ hướng → delta node
    DIR_DELTA = {
        90:  (-1,  0),   # Lên   (row giảm)
        270: ( 1,  0),   # Xuống (row tăng)
        180: ( 0, -1),   # Trái  (col giảm)
        0:   ( 0,  1),   # Phải  (col tăng)
    }

    def __init__(self):
        self.node_pos  = (1, 1)    # Vị trí node hiện tại (row, col)
        self.valid_dirs = []       # Tập hợp hướng hợp lệ chu kỳ này

    def update_from_pixel(self, pixel_pos, map_data, screen_width, screen_height):
        """Cập nhật node_pos từ pixel của AMR."""
        self.node_pos = turn2node(
            map_data, screen_width, screen_height,
            pixel_pos[0], pixel_pos[1]
        )

    def sense(self, map_data):
        """
        Chu kỳ cảm biến:
        Quét 4 hướng xung quanh, trả về tập hợp hướng không bị vật cản.
        """
        r, c   = self.node_pos
        rows   = len(map_data)
        cols   = len(map_data[0])
        result = []

        for heading, (dr, dc) in self.DIR_DELTA.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if map_data[nr][nc] == 0:
                    result.append(heading)

        self.valid_dirs = result
        return result

    def is_blocked(self, map_data, node):
        """Kiểm tra một node cụ thể có bị chặn không."""
        r, c = node
        if 0 <= r < len(map_data) and 0 <= c < len(map_data[0]):
            return map_data[r][c] != 0
        return True
