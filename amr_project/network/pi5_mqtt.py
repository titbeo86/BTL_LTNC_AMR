"""
network/pi5_mqtt.py — MQTT Client phía Raspberry Pi 5
Chạy trên Pi5, giao tiếp với Laptop qua Wi-Fi.

Nhiệm vụ:
  - PUB: amr/position  → gửi vị trí node hiện tại lên Laptop
  - PUB: amr/obstacle  → gửi vật cản phát hiện bởi camera
  - PUB: amr/status    → gửi trạng thái (IDLE/MOVING/ARRIVED)
  - SUB: amr/command   ← nhận lệnh từ Laptop
  - SUB: amr/path      ← nhận đường đi mới từ Laptop
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
    make_position, make_obstacle, make_status, make_heartbeat, parse
)


class Pi5MQTT:
    """
    MQTT client phía Raspberry Pi 5.
    Chạy trong background thread, thread-safe với main loop.
    """

    def __init__(self, broker_ip="localhost", broker_port=1883,
                 client_id="amr_pi5"):
        """
        broker_ip: IP của Laptop chạy Mosquitto broker.
                   Nếu broker chạy trên Pi5 thì để "localhost".
        """
        self.broker_ip   = broker_ip
        self.broker_port = broker_port
        self.client_id   = client_id

        self.connected   = False
        self.enabled     = False

        # Queue nhận lệnh từ Laptop → main loop Pi5 xử lý
        self.command_queue = queue.Queue(maxsize=50)
        self.path_queue    = queue.Queue(maxsize=10)
        self.config_queue  = queue.Queue(maxsize=10)

        self._client    = None
        self._thread    = None
        self._hb_thread = None

        # Throttle gửi position (tránh flood broker)
        self._last_pos_time = 0
        self.POS_INTERVAL   = 0.1   # Tối thiểu 100ms giữa 2 lần gửi

    # ── Kết nối ───────────────────────────────────

    def connect(self):
        if not MQTT_AVAILABLE:
            print("[Pi5 MQTT] paho-mqtt chưa cài.")
            print("  Chạy: pip install paho-mqtt --break-system-packages")
            return False

        try:
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id
            )
        except AttributeError:
            self._client = mqtt.Client(client_id=self.client_id)

        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message    = self._on_message

        # Auto-reconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=10)

        try:
            self._client.connect(self.broker_ip, self.broker_port,
                                 keepalive=60)
        except Exception as e:
            print(f"[Pi5 MQTT] Không kết nối được broker: {e}")
            return False

        self.enabled = True

        self._thread = threading.Thread(
            target=self._client.loop_forever,
            daemon=True, name="mqtt-pi5"
        )
        self._thread.start()

        self._hb_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True, name="mqtt-pi5-hb"
        )
        self._hb_thread.start()

        print(f"[Pi5 MQTT] Đang kết nối {self.broker_ip}:{self.broker_port}")
        return True

    def disconnect(self):
        self.enabled = False
        if self._client:
            self._client.disconnect()

    # ── Callbacks ────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc, *args):
        if rc == 0:
            self.connected = True
            print("[Pi5 MQTT] Kết nối thành công!")
            client.subscribe([
                (TOPIC_COMMAND,   QOS_AT_LEAST_ONCE),
                (TOPIC_PATH,      QOS_AT_LEAST_ONCE),
                (TOPIC_HEARTBEAT, QOS_AT_MOST_ONCE),
                (TOPIC_CONFIG,    QOS_AT_LEAST_ONCE),
            ])
        else:
            self.connected = False
            print(f"[Pi5 MQTT] Kết nối thất bại rc={rc}")

    def _on_disconnect(self, client, userdata, rc, *args):
        self.connected = False
        if rc != 0:
            print("[Pi5 MQTT] Mất kết nối, đang thử lại...")

    def _on_message(self, client, userdata, msg):
        data = parse(msg.payload)
        if not data:
            return
        try:
            if msg.topic == TOPIC_COMMAND:
                self.command_queue.put_nowait(data)
            elif msg.topic == TOPIC_PATH:
                # Xóa path cũ, nhận path mới
                while not self.path_queue.empty():
                    try: self.path_queue.get_nowait()
                    except queue.Empty: break
                self.path_queue.put_nowait(data)
            elif msg.topic == TOPIC_CONFIG:
                self.config_queue.put_nowait(data)
        except queue.Full:
            pass

    # ── Gửi dữ liệu lên Laptop ───────────────────

    def publish_position(self, row: int, col: int, heading: int = 0):
        """Gửi vị trí node hiện tại — throttled."""
        if not self.connected:
            return
        now = time.time()
        if now - self._last_pos_time < self.POS_INTERVAL:
            return
        self._last_pos_time = now
        self._client.publish(TOPIC_POSITION,
                             make_position(row, col, heading),
                             qos=QOS_AT_MOST_ONCE)

    def publish_obstacle(self, row: int, col: int,
                         source: str = "camera"):
        """Gửi vật cản mới phát hiện."""
        if not self.connected:
            return
        self._client.publish(TOPIC_OBSTACLE,
                             make_obstacle(row, col, source),
                             qos=QOS_AT_LEAST_ONCE)
        print(f"[Pi5 MQTT] Obstacle ({row},{col}) → Laptop")

    def publish_status(self, state: str, step: int = 0,
                       total: int = 0):
        """Gửi trạng thái AMR."""
        if not self.connected:
            return
        self._client.publish(TOPIC_STATUS,
                             make_status(state, step, total),
                             qos=QOS_AT_MOST_ONCE)

    # ── Poll từ main loop Pi5 ────────────────────

    def poll_commands(self) -> list:
        """Lấy tất cả lệnh đang chờ từ Laptop."""
        cmds = []
        while not self.command_queue.empty():
            try:
                cmds.append(self.command_queue.get_nowait())
            except queue.Empty:
                break
        return cmds

    def poll_path(self):
        """Lấy path mới nhất từ Laptop (hoặc None)."""
        try:
            return self.path_queue.get_nowait()
        except queue.Empty:
            return None

    def poll_config(self):
        """Lấy config mới nhất từ Laptop (hoặc None)."""
        try:
            return self.config_queue.get_nowait()
        except queue.Empty:
            return None

    # ── Heartbeat ────────────────────────────────

    def _heartbeat_loop(self):
        while self.enabled:
            if self.connected:
                try:
                    self._client.publish(
                        TOPIC_HEARTBEAT,
                        make_heartbeat("pi5"),
                        qos=QOS_AT_MOST_ONCE
                    )
                except Exception:
                    pass
            time.sleep(5)
