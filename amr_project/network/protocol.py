"""
network/protocol.py — Định nghĩa giao thức MQTT dùng chung
Cả Laptop và Pi5 đều import file này để đảm bảo topic/format nhất quán.

KIẾN TRÚC MQTT:
  Laptop (Subscriber + Publisher)
    ├── SUB: amr/position     ← Nhận vị trí thực tế từ Pi5
    ├── SUB: amr/obstacle     ← Nhận vật cản mới từ Camera
    ├── SUB: amr/status       ← Nhận trạng thái xe
    └── PUB: amr/command      → Gửi lệnh di chuyển cho Pi5

  Raspberry Pi 5 (Publisher + Subscriber)
    ├── PUB: amr/position     → Gửi vị trí node hiện tại
    ├── PUB: amr/obstacle     → Gửi vật cản phát hiện bởi camera
    ├── PUB: amr/status       → Gửi trạng thái (IDLE/MOVING/ARRIVED/...)
    └── SUB: amr/command      ← Nhận lệnh di chuyển từ Laptop
"""

import json
from dataclasses import dataclass, asdict


# ── Topics ────────────────────────────────────────
TOPIC_POSITION = "amr/position"    # Pi5 → Laptop
TOPIC_OBSTACLE = "amr/obstacle"    # Pi5 → Laptop
TOPIC_STATUS   = "amr/status"      # Pi5 → Laptop
TOPIC_COMMAND  = "amr/command"     # Laptop → Pi5
TOPIC_PATH     = "amr/path"        # Laptop → Pi5 (danh sách node đường đi)
TOPIC_HEARTBEAT= "amr/heartbeat"   # Cả hai hướng (kiểm tra kết nối)

# ── QoS Levels ───────────────────────────────────
QOS_AT_MOST_ONCE  = 0   # Fire-and-forget (vị trí real-time)
QOS_AT_LEAST_ONCE = 1   # Guaranteed (lệnh quan trọng)
QOS_EXACTLY_ONCE  = 2   # Đúng 1 lần (ít dùng, chậm hơn)


# ── Message builders ─────────────────────────────

def make_position(row: int, col: int, heading: int = 0) -> str:
    """
    Pi5 → Laptop: Vị trí hiện tại của AMR.
    {"row": 3, "col": 5, "heading": 0}
    """
    return json.dumps({"row": row, "col": col, "heading": heading})


def make_obstacle(row: int, col: int, source: str = "camera") -> str:
    """
    Pi5 → Laptop: Vật cản mới phát hiện bởi camera.
    {"row": 4, "col": 6, "source": "camera"}
    """
    return json.dumps({"row": row, "col": col, "source": source})


def make_status(state: str, step: int = 0, total: int = 0) -> str:
    """
    Pi5 → Laptop: Trạng thái AMR.
    {"state": "MOVING", "step": 3, "total": 10}
    """
    return json.dumps({"state": state, "step": step, "total": total})


def make_command(action: str, row: int = 0, col: int = 0,
                 heading: int = 0) -> str:
    """
    Laptop → Pi5: Lệnh di chuyển.
    action: "MOVE" | "STOP" | "GOTO" | "REPLAN"
    {"action": "MOVE", "heading": 90, "row": 3, "col": 5}
    """
    return json.dumps({
        "action":  action,
        "heading": heading,
        "row":     row,
        "col":     col,
    })


def make_path(path: list) -> str:
    """
    Laptop → Pi5: Toàn bộ đường đi.
    {"path": [[1,1],[1,2],[1,3],...]}
    """
    return json.dumps({"path": path})


def make_heartbeat(sender: str) -> str:
    """{"sender": "laptop"} hoặc {"sender": "pi5"}"""
    import time
    return json.dumps({"sender": sender, "ts": round(time.time(), 2)})


# ── Message parsers ──────────────────────────────

def parse(payload: bytes) -> dict:
    """Parse raw MQTT payload → dict. Trả về {} nếu lỗi."""
    try:
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return {}


# ── Thêm: lệnh thay đổi kích thước ô ─────────────
TOPIC_CONFIG = "amr/config"   # Laptop → Pi5 + ESP32

def make_config_cell(cell_mm: int) -> str:
    """
    Laptop → Pi5 → ESP32: thay đổi kích thước ô.
    {"type": "cell_mm", "value": 200}
    """
    return json.dumps({"type": "cell_mm", "value": cell_mm})


def make_config_speed(pwm: int) -> str:
    """Thay đổi tốc độ PWM mặc định."""
    return json.dumps({"type": "speed", "value": pwm})
