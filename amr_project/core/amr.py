"""
AMR module — Đối tượng robot tự hành
Giữ nguyên hàm gốc, bổ sung:
  - node_pos: vị trí hiện tại trên tọa độ NODE (row, col)
  - snap_to_node(): snap chính xác vào node sau mỗi bước
"""

import math


class Amrs(object):

    def __init__(self, amrDimension=[30, 25], position=[0, 0], orientation=90):
        self.width    = amrDimension[0]
        self.height   = amrDimension[1]
        self.pos      = list(position)   # Tọa độ PIXEL [x, y]
        self.heading  = orientation
        self.draw_heading = orientation
        self.color    = (0, 200, 0)
        self.path_points = [tuple(position)]
        self.speed    = 8               # pixel/frame
        self.node_pos = (1, 1)          # Tọa độ NODE (row, col) — cập nhật bởi sensor

    # ── Giữ nguyên từ code gốc ──────────────────

    def moveForward(self, distance):
        rad = math.radians(self.heading)
        self.pos[0] += math.cos(rad) * distance
        self.pos[1] -= math.sin(rad) * distance
        self.path_points.append(tuple(self.pos))

    def turnLeft(self):
        self.heading = 180

    def turnRight(self):
        self.heading = 0

    def turnUp(self):
        self.heading = 270

    def turnDown(self):
        self.heading = 90
