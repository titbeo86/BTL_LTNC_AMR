"""
network/laptop_mqtt.py — MQTT Client phía Laptop
Chạy trong thread riêng, không block GUI Pygame.

Nhiệm vụ:
  - Kết nối Mosquitto broker (chạy trên Laptop hoặc Pi5)
  - SUB: amr/position  → cập nhật vị trí AMR lên Digital Twin
  - SUB: amr/obstacle  → thêm vật cản mới lên map, trigger replanning
  - SUB: amr/status    → cập nhật trạng thái hiển thị
  - PUB: amr/command   → gửi lệnh đến Pi5
  - PUB: amr/path      → gửi đường đi mới khi replanning
"""

import threading
import queue
import time

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

from network.protocol import (
    TOPIC_POSITION, TOPIC_OBSTACLE, TOPIC_STATUS,
    TOPIC_COMMAND, TOPIC_PATH, TOPIC_HEARTBEAT, TOPIC_CONFIG,
    QOS_AT_MOST_ONCE, QOS_AT_LEAST_ONCE,
    make_command, make_path, make_heartbeat, make_config_cell, parse
)


class LaptopMQTT:
    """
    MQTT client phía Laptop, chạy trong background thread.
    GUI Pygame poll queue để nhận events, không cần callback trực tiếp.
    """

    def __init__(self, broker_ip="localhost", broker_port=1883,
                 client_id="amr_laptop"):
        self.broker_ip   = broker_ip
        self.broker_port = broker_port
        self.client_id   = client_id

        self.connected   = False
        self.enabled     = False

        # Queue thread-safe: PI5 → Laptop events
        # Mỗi event: {"type": "position"/"obstacle"/"status", ...}
        self.event_queue = queue.Queue(maxsize=100)

        self._client     = None
        self._thread     = None
        self._hb_thread  = None

    # ── Kết nối ───────────────────────────────────

    def connect(self):
        """Kết nối đến broker, chạy loop trong thread riêng."""
        if not MQTT_AVAILABLE:
            print("[MQTT] paho-mqtt chưa cài. Chạy: pip install paho-mqtt")
            return False

        try:
            # paho-mqtt 2.x API
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id
            )
        except AttributeError:
            # paho-mqtt 1.x fallback
            self._client = mqtt.Client(client_id=self.client_id)

        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message    = self._on_message

        try:
            self._client.connect(self.broker_ip, self.broker_port,
                                 keepalive=60)
        except Exception as e:
            print(f"[MQTT] Không kết nối được: {e}")
            return False

        self.enabled = True
        # Chạy network loop trong thread riêng
        self._thread = threading.Thread(
            target=self._client.loop_forever,
            daemon=True, name="mqtt-laptop"
        )
        self._thread.start()

        # Heartbeat thread
        self._hb_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True, name="mqtt-heartbeat"
        )
        self._hb_thread.start()

        print(f"[MQTT] Đang kết nối {self.broker_ip}:{self.broker_port}...")
        return True

    def disconnect(self):
        self.enabled = False
        if self._client:
            self._client.disconnect()

    # ── Callbacks từ broker ───────────────────────

    def _on_connect(self, client, userdata, flags, rc, *args):
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Laptop kết nối thành công!")
            # Subscribe các topic cần nhận
            client.subscribe([
                (TOPIC_POSITION,  QOS_AT_MOST_ONCE),
                (TOPIC_OBSTACLE,  QOS_AT_LEAST_ONCE),
                (TOPIC_STATUS,    QOS_AT_MOST_ONCE),
                (TOPIC_HEARTBEAT, QOS_AT_MOST_ONCE),
            ])
        else:
            self.connected = False
            print(f"[MQTT] Kết nối thất bại, rc={rc}")

    def _on_disconnect(self, client, userdata, rc, *args):
        self.connected = False
        if rc != 0:
            print(f"[MQTT] Mất kết nối (rc={rc}), tự kết nối lại...")

    def _on_message(self, client, userdata, msg):
        """Nhận message từ Pi5 → đẩy vào queue cho GUI xử lý."""
        data = parse(msg.payload)
        if not data:
            return

        topic = msg.topic
        try:
            if topic == TOPIC_POSITION:
                # {"row": 3, "col": 5, "heading": 0}
                self.event_queue.put_nowait({
                    "type": "position",
                    "row":  data.get("row", 0),
                    "col":  data.get("col", 0),
                    "heading": data.get("heading", 0),
                })
            elif topic == TOPIC_OBSTACLE:
                # {"row": 4, "col": 6, "source": "camera"}
                self.event_queue.put_nowait({
                    "type":   "obstacle",
                    "row":    data.get("row", 0),
                    "col":    data.get("col", 0),
                    "source": data.get("source", "unknown"),
                })
            elif topic == TOPIC_STATUS:
                # {"state": "MOVING", "step": 3, "total": 10}
                self.event_queue.put_nowait({
                    "type":  "status",
                    "state": data.get("state", "IDLE"),
                    "step":  data.get("step",  0),
                    "total": data.get("total", 0),
                })
            elif topic == TOPIC_HEARTBEAT:
                if data.get("sender") == "pi5":
                    self.event_queue.put_nowait({"type": "heartbeat_pi5"})
        except queue.Full:
            pass  # Bỏ qua nếu queue đầy

    # ── Gửi lệnh đến Pi5 ──────────────────────────

    def send_command(self, action: str, heading: int = 0,
                     row: int = 0, col: int = 0):
        """Gửi lệnh di chuyển đến Pi5."""
        if not self.connected:
            return
        payload = make_command(action, row, col, heading)
        self._client.publish(TOPIC_COMMAND, payload,
                             qos=QOS_AT_LEAST_ONCE)

    def send_cell_config(self, cell_mm: int):
        """Gửi cấu hình kích thước ô (cell size) lên Pi5."""
        if not self.connected:
            return
        payload = make_config_cell(cell_mm)
        self._client.publish(TOPIC_CONFIG, payload,
                             qos=QOS_AT_LEAST_ONCE)
        print(f"[MQTT] Gửi cell_config: {cell_mm}mm → Pi5")

    def send_path(self, path: list):
        """
        Gửi đường đi mới đến Pi5 (danh sách node [(r,c),...]).
        Pi5 sẽ thực thi từng bước theo path này.
        """
        if not self.connected or not path:
            return
        payload = make_path(path)
        self._client.publish(TOPIC_PATH, payload,
                             qos=QOS_AT_LEAST_ONCE)
        print(f"[MQTT] Gửi path {len(path)} bước → Pi5")

    def send_stop(self):
        """Dừng khẩn cấp."""
        self.send_command("STOP")

    # ── Poll events từ queue (gọi từ GUI loop) ────

    def poll(self) -> list:
        """
        Lấy tất cả events đang chờ trong queue.
        Gọi mỗi frame trong Pygame loop.
        Trả về list events.
        """
        events = []
        while not self.event_queue.empty():
            try:
                events.append(self.event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    # ── Heartbeat ────────────────────────────────

    def _heartbeat_loop(self):
        while self.enabled:
            if self.connected:
                payload = make_heartbeat("laptop")
                try:
                    self._client.publish(TOPIC_HEARTBEAT, payload,
                                         qos=QOS_AT_MOST_ONCE)
                except Exception:
                    pass
            time.sleep(5)

    # ── Status ───────────────────────────────────

    @property
    def status_text(self) -> str:
        if not MQTT_AVAILABLE:
            return "MQTT: NOT INSTALLED"
        if not self.enabled:
            return "MQTT: DISABLED"
        if not self.connected:
            return "MQTT: CONNECTING..."
        return f"MQTT: {self.broker_ip}"
