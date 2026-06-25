"""
Actuator module — Thực thi di chuyển AMR
Nhận hướng (0/90/180/270) từ Processor,
di chuyển AMR đúng 1 ô theo trục x hoặc y.
Hỗ trợ 2 chế độ:
  - INSTANT: nhảy ngay 1 ô (đúng 1 chu kỳ)
  - SMOOTH : animation mượt về đích (nhiều frame)
"""

from utils.utils import turn2pixel


class Actuators(object):

    MODE_INSTANT = "INSTANT"
    MODE_SMOOTH  = "SMOOTH"

    # Delta pixel theo hướng (tính khi set_target)
    DIR_DELTA = {
        90:  (-1,  0),
        270: ( 1,  0),
        180: ( 0, -1),
        0:   ( 0,  1),
    }

    def __init__(self, mode=MODE_SMOOTH):
        self.mode          = mode
        self.moving        = False
        self._target_pixel = None
        self.TOLERANCE     = 3       # pixel

    def set_target(self, target_node, map_data, screen_width, screen_height):
        """Đặt node đích tiếp theo."""
        self._target_pixel = turn2pixel(
            map_data, screen_height, screen_width,
            target_node[0], target_node[1]
        )
        self.moving = True

    def execute(self, amr, map_data, screen_width, screen_height):
        """
        Thực thi di chuyển 1 bước.
        Trả về True khi đã đến node đích (hoàn thành 1 chu kỳ di chuyển).
        """
        if not self.moving or self._target_pixel is None:
            return False

        tx, ty = self._target_pixel

        if self.mode == self.MODE_INSTANT:
            # Nhảy ngay 1 ô — hoàn thành trong 1 frame
            amr.pos[0] = tx
            amr.pos[1] = ty
            amr.path_points.append(tuple(amr.pos))
            self.moving = False
            return True

        # SMOOTH: di chuyển từng frame
        cx, cy = amr.pos[0], amr.pos[1]
        dx = tx - cx
        dy = ty - cy
        dist = (dx**2 + dy**2) ** 0.5

        if dist <= self.TOLERANCE:
            # Snap chính xác vào node
            amr.pos[0] = tx
            amr.pos[1] = ty
            amr.path_points.append(tuple(amr.pos))
            self.moving = False
            return True

        step = min(amr.speed, dist)
        amr.pos[0] += (dx / dist) * step
        amr.pos[1] += (dy / dist) * step

        # Cập nhật heading để vẽ đúng chiều
        import math
        angle = math.degrees(math.atan2(-dy, dx))
        if angle < 0:
            angle += 360
        amr.heading = round(angle / 90) * 90 % 360

        return False

    def cancel(self):
        self.moving        = False
        self._target_pixel = None
