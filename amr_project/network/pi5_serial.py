"""
network/pi5_serial.py — Giao tiếp Serial Pi5 ↔ ESP32
Giao thức: JSON line-based, mỗi lệnh 1 dòng kết thúc \\n

Laptop→Pi5→ESP32 command format:
  {"cmd": "MOVE", "heading": 90, "row": 3, "col": 5}
  {"cmd": "TURN", "angle": 90}
  {"cmd": "STOP"}
  {"cmd": "SPEED", "v": 150}

ESP32→Pi5 response format:
  {"ack": "DONE", "node": [3,5]}     # Hoàn thành 1 bước, vị trí hiện tại
  {"ack": "TURN_DONE", "heading": 0} # Hoàn thành xoay
  {"ack": "BUSY"}                     # Đang di chuyển
  {"ack": "ERROR", "msg": "..."}     # Lỗi
  {"pos": [3,5], "heading": 90}      # Cập nhật vị trí định kỳ
"""

import json
import threading
import queue
import time

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class Pi5Serial:

    def __init__(self, port="/dev/ttyUSB0", baud=115200):
        self.port      = port
        self.baud      = baud
        self._ser      = None
        self._busy     = False       # ESP32 đang di chuyển
        self._lock     = threading.Lock()
        self._rx_thread= None
        self.connected = False

        # Event queue thay vì callback trực tiếp (thread-safe)
        # Mỗi event: {"type": "MOVE_DONE", "node": (r,c)} hoặc {"type": "TURN_DONE"}
        self.event_queue = queue.Queue(maxsize=50)

    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            print("[Serial] pyserial chưa cài.")
            return False
        try:
            self._ser = serial.Serial(
                port     = self.port,
                baudrate = self.baud,
                timeout  = 1.0
            )
            time.sleep(2)   # Chờ ESP32 reset
            self.connected = True
            # Bắt đầu thread đọc phản hồi
            self._rx_thread = threading.Thread(
                target=self._read_loop,
                daemon=True, name="serial-rx"
            )
            self._rx_thread.start()
            print(f"[Serial] Kết nối {self.port} @ {self.baud} baud OK")
            return True
        except Exception as e:
            print(f"[Serial] Lỗi kết nối {self.port}: {e}")
            return False

    def disconnect(self):
        self.connected = False
        if self._ser and self._ser.is_open:
            self._ser.close()

    def send_move(self, heading: int, speed: int = 250,
                  row: int = 0, col: int = 0):
        """Gửi lệnh di chuyển 1 ô — bao gồm tọa độ đích."""
        cmd = json.dumps({"cmd": "MOVE",
                          "heading": heading,
                          "speed": speed,
                          "row": row,
                          "col": col})
        self._send_raw(cmd)
        self._busy = True

        # Nếu đang chạy mô phỏng (không cắm ESP32)
        if not self.connected:
            def _simulate_ack():
                time.sleep(0.8)
                self._busy = False
                print("[Serial SIM] ESP32 giả lập MOVE DONE.")
                try:
                    self.event_queue.put_nowait({
                        "type": "MOVE_DONE",
                        "node": (row, col)
                    })
                except queue.Full:
                    pass
            threading.Thread(target=_simulate_ack, daemon=True).start()

    def send_turn(self, angle: int):
        """Gửi lệnh bẻ lái tại chỗ (Tank turn)."""
        cmd = json.dumps({"cmd": "TURN", "angle": angle})
        self._send_raw(cmd)
        self._busy = True

        if not self.connected:
            def _simulate_ack():
                time.sleep(0.5)
                self._busy = False
                print("[Serial SIM] ESP32 giả lập TURN DONE.")
                try:
                    self.event_queue.put_nowait({"type": "TURN_DONE"})
                except queue.Full:
                    pass
            threading.Thread(target=_simulate_ack, daemon=True).start()

    def send_stop(self):
        """Dừng khẩn cấp."""
        self._send_raw(json.dumps({"cmd": "STOP"}))
        self._busy = False

    def send_speed(self, speed: int):
        """Đặt tốc độ (0-255)."""
        self._send_raw(json.dumps({"cmd": "SPEED", "v": speed}))

    def send_cell_size(self, mm: int):
        """Gửi cấu hình kích thước ô (cell size) xuống ESP32."""
        self._send_raw(json.dumps({"cmd": "CELL", "mm": mm}))

    def send_reset(self, row: int = 1, col: int = 1, heading: int = 90):
        """Gửi lệnh reset vị trí và hướng xuống ESP32."""
        self._send_raw(json.dumps({"cmd": "RESET", "row": row, "col": col, "heading": heading}))
        self._busy = False

    def is_busy(self) -> bool:
        return self._busy

    def poll_events(self) -> list:
        """Lấy tất cả events từ ESP32 (thread-safe). Gọi từ main loop."""
        events = []
        while not self.event_queue.empty():
            try:
                events.append(self.event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def _send_raw(self, text: str):
        if not self.connected or self._ser is None:
            # Mô phỏng: print ra console
            print(f"[Serial SIM] TX: {text}")
            return
        with self._lock:
            try:
                self._ser.write((text + "\n").encode("utf-8"))
            except Exception as e:
                print(f"[Serial] Lỗi gửi: {e}")

    def _read_loop(self):
        """Đọc phản hồi từ ESP32 liên tục."""
        while self.connected:
            try:
                if self._ser and self._ser.in_waiting:
                    line = self._ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        self._parse_rx(line)
            except Exception as e:
                print(f"[Serial] Lỗi đọc: {e}")
            time.sleep(0.01)

    def _parse_rx(self, line: str):
        """Xử lý phản hồi từ ESP32 → đẩy vào event queue."""
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            # Nếu không phải JSON, in thẳng ra console để debug (rất quan trọng)
            print(f"> {line}")
            return

        ack = data.get("ack", "")

        if ack == "DONE":
            self._busy = False
            node = data.get("node", None)
            print(f"[Serial] ESP32 DONE tại {node}")
            if node:
                try:
                    self.event_queue.put_nowait({
                        "type": "MOVE_DONE",
                        "node": tuple(node)
                    })
                except queue.Full:
                    pass

        elif ack == "TURN_DONE":
            self._busy = False
            heading = data.get("heading", None)
            print(f"[Serial] ESP32 TURN_DONE hướng {heading}°")
            try:
                self.event_queue.put_nowait({"type": "TURN_DONE"})
            except queue.Full:
                pass

        elif ack == "BUSY":
            self._busy = True

        elif ack == "ERROR":
            msg = data.get('msg', '')
            print(f"[Serial] ESP32 ERROR: {msg}")
            self._busy = False
            try:
                self.event_queue.put_nowait({
                    "type": "ERROR",
                    "msg": msg
                })
            except queue.Full:
                pass

        elif "pos" in data:
            # Cập nhật vị trí định kỳ từ ESP32 (mỗi 500ms)
            pos = data.get("pos", None)
            if pos:
                try:
                    self.event_queue.put_nowait({
                        "type": "POS_UPDATE",
                        "node": tuple(pos)
                    })
                except queue.Full:
                    pass
