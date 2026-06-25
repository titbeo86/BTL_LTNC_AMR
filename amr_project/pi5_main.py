"""
pi5_main.py — Script chính chạy trên Raspberry Pi 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Luồng hoạt động:
  1. Kết nối MQTT → Laptop
  2. Kết nối Serial → ESP32
  3. Vòng lặp chính:
     a. Poll MQTT: nhận path / lệnh từ Laptop
     b. Poll Serial events: nhận phản hồi ESP32 (DONE/TURN_DONE)
     c. Gửi lệnh di chuyển từng bước xuống ESP32
     d. Publish vị trí hiện tại lên Laptop

Chạy: python3 pi5_main.py --broker 192.168.1.x --port /dev/ttyUSB0
"""

import time
import argparse

from network.pi5_mqtt   import Pi5MQTT
from network.pi5_serial import Pi5Serial


# ── Cấu hình mặc định ────────────────────────────
DEFAULT_BROKER = "192.168.2.9"   # IP MQTT Broker
DEFAULT_SERIAL = "/dev/ttyUSB0"  # Cổng Serial kết nối ESP32
DEFAULT_BAUD   = 115200


class Pi5Controller:
    """
    Bộ điều khiển trung tâm trên Raspberry Pi 5.
    Phối hợp MQTT ↔ Serial.
    """

    def __init__(self, broker_ip: str, serial_port: str, baud: int):
        # MQTT
        self.mqtt   = Pi5MQTT(broker_ip=broker_ip)

        # Serial tới ESP32
        self.serial = Pi5Serial(port=serial_port, baud=baud)

        # Trạng thái nội bộ
        self.current_node   = (1, 1)
        self.current_position = [1.0, 1.0] # Tọa độ liên tục để truyền mượt lên Laptop
        self.current_facing = 0        # Hướng mặt xe (0=Bắc, 90=Đông, 180=Nam, 270=Tây)
        self.path           = []       # [(r,c), ...]
        self.path_index     = 0
        self.state          = "IDLE"
        self.running        = True

        # Non-blocking delay sau khi TURN xong
        self._turn_cooldown_until = 0  # timestamp (millis)
        self._retry_count = 0          # Đếm số lần retry khi ESP32 timeout

    def start(self):
        print("=" * 50)
        print("  AMR Pi5 Controller — Khởi động")
        print("=" * 50)

        # Kết nối MQTT
        if not self.mqtt.connect():
            print("[ERROR] Không kết nối được MQTT broker!")
            return

        # Kết nối Serial ESP32
        if not self.serial.connect():
            print("[WARN] Không kết nối được ESP32 — chạy mô phỏng")

        # Chờ MQTT kết nối xong
        for _ in range(20):
            if self.mqtt.connected:
                break
            time.sleep(0.5)

        if not self.mqtt.connected:
            print("[ERROR] MQTT không kết nối được sau 10s!")
            return

        print("[OK] Sẵn sàng nhận lệnh từ Laptop...")
        self.mqtt.publish_status("IDLE")

        # Vòng lặp chính
        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n[Pi5] Dừng bởi người dùng.")
        finally:
            self.mqtt.publish_status("OFFLINE")
            self.mqtt.disconnect()
            self.serial.disconnect()

    def _main_loop(self):
        while self.running:
            # ── 1. Poll lệnh từ Laptop ──
            self._process_mqtt()

            # ── 2. Poll phản hồi từ ESP32 (thread-safe queue) ──
            self._process_serial_events()

            # ── 3. Thực thi di chuyển ──
            self._execute_movement()

            # ── 4. Publish vị trí ──
            self.mqtt.publish_position(
                self.current_position[0],
                self.current_position[1],
                self.current_facing
            )

            time.sleep(0.05)   # 20 Hz

    def _process_mqtt(self):
        """Xử lý commands và path mới từ Laptop."""
        # Path mới
        path_data = self.mqtt.poll_path()
        if path_data and "path" in path_data:
            raw = path_data["path"]
            self.path       = [tuple(p) for p in raw]
            self.path_index = 0
            self.current_node = self.path[0] if self.path else (1, 1)
            self.current_position = [float(self.current_node[0]), float(self.current_node[1])]
            self.state      = "MOVING"
            print(f"[Pi5] Nhận path mới: {len(self.path)} bước")
            self.mqtt.publish_status("MOVING", 0, len(self.path)-1)
            
            # Đồng bộ tọa độ bắt đầu xuống ESP32 trước khi chạy
            esp_heading = (90 - self.current_facing) % 360
            self.serial.send_reset(row=self.current_node[0], col=self.current_node[1], heading=esp_heading)

        # Config mới (kích thước ô)
        config_data = self.mqtt.poll_config()
        if config_data and config_data.get("type") == "cell_mm":
            cell_mm = config_data.get("value", 200)
            print(f"[Pi5] Nhận cấu hình cell size mới: {cell_mm}mm")
            self.serial.send_cell_size(cell_mm)

        # Commands
        for cmd in self.mqtt.poll_commands():
            action = cmd.get("action", "")
            if action == "STOP":
                self.state = "IDLE"
                self.path  = []
                self.serial.send_stop()
                self.mqtt.publish_status("IDLE")
                print("[Pi5] DỪNG khẩn cấp!")

            elif action == "RESET":
                self.state = "IDLE"
                self.path  = []
                self.path_index = 0
                self.current_node = (1, 1)
                self.current_position = [1.0, 1.0]
                self.current_facing = 0
                self.serial.send_reset(row=1, col=1, heading=90)
                self.mqtt.publish_status("IDLE")
                print("[Pi5] RESET vị trí về (1,1)!")

            elif action == "REPLAN":
                self.state = "WAIT_PATH"
                self.serial.send_stop()

    def _process_serial_events(self):
        """Xử lý events từ ESP32 (thread-safe, non-blocking)."""
        for ev in self.serial.poll_events():
            ev_type = ev.get("type", "")

            if ev_type == "MOVE_DONE":
                # ESP32 đã di chuyển xong 1 ô
                node = ev.get("node")
                if self.state == "MOVING" and self.path and node:
                    try:
                        # Tìm vị trí của node đích trong mảng path
                        idx = self.path.index((round(node[0]), round(node[1])), self.path_index)
                        if idx > self.path_index:
                            self.current_node = self.path[idx]
                            self.path_index   = idx
                            self.current_position = [float(self.current_node[0]), float(self.current_node[1])]
                            # Báo cáo vị trí mới lên Laptop để đồng bộ xe ảo
                            self.mqtt.publish_position(
                                self.current_position[0],
                                self.current_position[1],
                                self.current_facing
                            )
                            self.mqtt.publish_status(
                                "MOVING", idx, len(self.path)-1
                            )
                            print(f"[Pi5] Đã đến node {self.current_node} "
                                  f"({idx}/{len(self.path)-1})")
                    except ValueError:
                        pass
                self._retry_count = 0  # Reset retry khi thành công

            elif ev_type == "TURN_DONE":
                # ESP32 đã xoay xong
                # Non-blocking delay 0.5s để giảm quán tính
                self._turn_cooldown_until = time.time() + 0.5
                print("[Pi5] Xoay xong, chờ 0.5s ổn định...")
                self._retry_count = 0  # Reset retry khi thành công

            elif ev_type == "POS_UPDATE":
                node = ev.get("node")
                if self.state == "MOVING" and self.path and node:
                    try:
                        int_node = (round(node[0]), round(node[1]))
                        idx = self.path.index(int_node, self.path_index)
                        if idx > self.path_index:
                            self.current_node = self.path[idx]
                            self.path_index   = idx
                            self.mqtt.publish_status(
                                "MOVING", idx, len(self.path)-1
                            )
                        self.current_position = [node[0], node[1]]
                        print(f"[Pi5] Cập nhật vị trí trung gian: ({node[0]:.3f}, {node[1]:.3f})")
                        self.mqtt.publish_position(
                            self.current_position[0],
                            self.current_position[1],
                            self.current_facing
                        )
                    except ValueError:
                        pass

            elif ev_type == "ERROR":
                msg = ev.get("msg", "")
                print(f"[Pi5] ESP32 lỗi: {msg}")
                if msg == "TIMEOUT":
                    self._retry_count += 1
                    if self._retry_count >= 3:
                        print("[Pi5] ĐÃ THỬ 3 LẦN — DỪNG! Kiểm tra phần cứng ESP32.")
                        self.state = "IDLE"
                        self.path  = []
                        self.serial.send_stop()
                        self.mqtt.publish_status("ERROR")
                        self._retry_count = 0
                    else:
                        print(f"[Pi5] ESP32 timeout, thử lại lần {self._retry_count}/3...")

    def _execute_movement(self):
        """Gửi lệnh di chuyển từng bước xuống ESP32.
        
        Logic (không dùng Mecanum lateral):
        - Xe luôn đi THẲNG (heading=90, 4 bánh cùng chiều)
        - Khi cần rẽ: gửi TURN trước → chờ xong → gửi MOVE
        """
        if self.state != "MOVING" or not self.path:
            return

        # Kiểm tra ESP32 đã hoàn thành bước trước chưa
        if self.serial.is_busy():
            return

        # Kiểm tra cooldown sau TURN (non-blocking)
        if time.time() < self._turn_cooldown_until:
            return

        # Đã đến đích
        if self.path_index >= len(self.path) - 1:
            self.state = "ARRIVED"
            self.mqtt.publish_status("ARRIVED",
                                      len(self.path)-1, len(self.path)-1)
            print(f"[Pi5] ĐÃ ĐẾN ĐÍCH {self.current_node}")
            return

        # Bước tiếp theo
        next_idx  = self.path_index + 1
        next_node = self.path[next_idx]
        cur_node  = self.path[self.path_index]

        # Tính hướng cần đi
        dr = next_node[0] - cur_node[0]
        dc = next_node[1] - cur_node[1]
        required_facing = self._delta_to_facing(dr, dc)

        if required_facing is None:
            print(f"[Pi5] Lỗi delta ({dr},{dc})")
            return

        # Nếu xe chưa quay đúng hướng → gửi TURN trước
        if self.current_facing != required_facing:
            turn_angle = self._calc_turn_angle(
                self.current_facing, required_facing)
            self.current_facing = required_facing
            self.serial.send_turn(turn_angle)
            dir_name = self._facing_name(required_facing)
            print(f"[Pi5] XOAY {turn_angle}° → hướng {dir_name}")
            return  # Chờ TURN xong rồi mới MOVE ở vòng lặp sau

        # Tìm node XA NHẤT trên cùng một đường thẳng
        target_idx = next_idx
        while target_idx + 1 < len(self.path):
            n1 = self.path[target_idx]
            n2 = self.path[target_idx + 1]
            ndr = n2[0] - n1[0]
            ndc = n2[1] - n1[1]
            if self._delta_to_facing(ndr, ndc) == required_facing:
                target_idx += 1
            else:
                break
                
        target_node = self.path[target_idx]

        # Xe đã quay đúng hướng → gửi MOVE thẳng 1 đoạn dài (KÈM TỌA ĐỘ ĐÍCH)
        self.serial.send_move(
            heading=required_facing,
            speed=160,
            row=target_node[0],
            col=target_node[1]
        )
        dir_name = self._facing_name(self.current_facing)
        print(f"[Pi5] ĐI THẲNG {target_idx - self.path_index} ô → {target_node} ({dir_name})")

    # ── Helper methods ──────────────────────────────
    
    def _delta_to_facing(self, dr, dc) -> int:
        """Chuyển delta (dr,dc) → hướng mặt xe (0=Bắc, 90=Đông, 180=Nam, 270=Tây)."""
        table = {
            ( 1,  0): 0,     # Lên    → mặt hướng Bắc
            (-1,  0): 180,   # Xuống  → mặt hướng Nam
            ( 0, -1): 270,   # Trái   → mặt hướng Tây
            ( 0,  1): 90,    # Phải   → mặt hướng Đông
        }
        return table.get((dr, dc), None)



    def _calc_turn_angle(self, current: int, target: int) -> int:
        """Tính góc xoay ngắn nhất (-180..180)."""
        diff = (target - current) % 360
        if diff > 180:
            diff -= 360
        return diff

    def _facing_name(self, facing: int) -> str:
        """Tên hướng mặt xe."""
        names = {0: "BAC", 90: "DONG", 180: "NAM", 270: "TAY"}
        return names.get(facing, "---")


# ─────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AMR Pi5 Controller")
    parser.add_argument("--broker", default=DEFAULT_BROKER,
                        help=f"IP Laptop (Mosquitto broker), mặc định: {DEFAULT_BROKER}")
    parser.add_argument("--port",   default=DEFAULT_SERIAL,
                        help=f"Cổng Serial ESP32, mặc định: {DEFAULT_SERIAL}")
    parser.add_argument("--baud",   default=DEFAULT_BAUD, type=int,
                        help=f"Baud rate, mặc định: {DEFAULT_BAUD}")
    args = parser.parse_args()

    ctrl = Pi5Controller(
        broker_ip   = args.broker,
        serial_port = args.port,
        baud        = args.baud,
    )
    ctrl.start()
