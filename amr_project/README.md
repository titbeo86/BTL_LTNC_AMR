# 🐍 BỘ PHẦN MỀM ĐIỀU KHIỂN & MÔ PHỎNG AMR (PYTHON APPLICATION)

Thư mục này chứa mã nguồn **Python** chạy trên Laptop (dành cho bộ mô phỏng 2D Digital Twin và xử lý các thuật toán tìm đường nâng cao) và chạy trên Raspberry Pi 5 (bộ điều khiển phối hợp trung tâm).

---

## 📂 Cấu Trúc Mã Nguồn

```text
amr_project/
├── component/               # Các khối chức năng ảo mô phỏng phần cứng
│   ├── sensor.py            # Quét 4 hướng xung quanh xe xem có vật cản hay không
│   ├── actuator.py          # Nội suy pixel chuyển động mượt xe ảo
│   └── processor.py         # Bộ não phối hợp thuật toán và đích
├── core/                    # Lớp điều khiển chính của simulator
│   ├── amr.py               # Thuộc tính xe ảo (kích thước, hướng vẽ)
│   ├── application.py       # Quản lý giao diện, các luồng MQTT và vòng lặp trò chơi
│   ├── graphic.py           # Vẽ bản đồ, lưới ô vuông, panel thông tin HUD
│   ├── input.py             # Sự kiện chuột, bàn phím điều khiển
│   ├── map.py               # Khởi tạo ma trận bản đồ
│   ├── map_editor.py        # Vẽ tường/xóa tường trực tiếp bằng chuột
│   └── waypoint_manager.py  # Quản lý danh sách các điểm đi qua liên tục
├── network/                 # Thư viện giao tiếp không dây
│   ├── laptop_mqtt.py       # MQTT Client chạy ngầm phía Laptop
│   ├── pi5_mqtt.py          # MQTT Client chạy ngầm phía Raspberry Pi 5
│   ├── pi5_serial.py        # Driver Serial giao tiếp với ESP32
│   └── protocol.py          # Giao thức định nghĩa cấu trúc gói tin JSON dùng chung
├── utils/                   # Hàm tiện ích chuyển đổi tọa độ
│   └── utils.py             # Chuyển đổi tọa độ ô vật lý sang tọa độ pixel màn hình
├── main.py                  # Entrypoint chạy giao diện Laptop GUI
└── pi5_main.py              # Script chính chạy trên Raspberry Pi 5
```

---

## 💻 1. Giao Diện Mô Phỏng Trên Laptop (`main.py`)

Giao diện chính được xây dựng bằng **Pygame**, tối ưu hóa hiển thị, hỗ trợ màn hình cấu hình động lưới bản đồ từ `5x5` đến `50x50` ô, và cỡ ô thực tế từ `5cm` đến `200cm`.

### Phím tắt điều khiển GUI:
* `1` - `6` : Đổi nhanh thuật toán (`BFS`, `Dijkstra`, `Q-Learning (RL)`, `Greedy`, `GWF (Tu thiet ke)`, `ACO (Ant Colony)`).
* `SPACE` (Khoảng cách): Tính toán đường đi theo thuật toán đã chọn.
* `ENTER` : Kích hoạt bước đi tiếp theo (hoặc truyền lộ trình xuống xe thực).
* `A` : Bật/Tắt chế độ tự động di chuyển đến đích (Auto-run).
* `R` : Reset xe ảo và thực tế về điểm xuất phát mặc định `(1,1)`.
* `N` : Sinh ngẫu nhiên bản đồ chướng ngại vật mới (Xác suất 18%).
* `E` : Bật/Tắt chế độ chỉnh sửa bản đồ bằng chuột (Map Editor).
* `W` : Bật/Tắt chế độ đa điểm đích (Waypoint Mode).
* `F` : Bật/Tắt vẽ lưới năng lượng / khoảng cách (Cost Field) làm nền.
* `Z` : Chạy hiệu ứng trực quan hóa (Animation) hoạt động của thuật toán.
* `ESC` : Thoát ra màn hình cấu hình lưới ban đầu.

---

## 🍓 2. Bộ Điều Khiển Trung Tâm Trên Raspberry Pi 5 (`pi5_main.py`)

Raspberry Pi 5 đóng vai trò là "Cầu nối giao tiếp trung tâm" kết nối máy tính qua Wi-Fi MQTT và kết nối ESP32 qua Serial USB.

### Luồng xử lý chính:
1. Kết nối vào MQTT Broker của Laptop, đăng ký lắng nghe (Subscribe) các kênh:
   - `amr/path`: Nhận đường đi dài cần di chuyển.
   - `amr/command`: Nhận các lệnh khẩn cấp như `STOP`, `RESET`.
2. Lắng nghe Serial từ ESP32: Nhận tín hiệu `DONE` (đã đi xong 1 ô), `TURN_DONE` (đã xoay xong), hoặc `POS_UPDATE` (tọa độ thực nội suy từ Encoder động cơ).
3. Quản lý trạng thái di chuyển:
   - Nếu hướng mặt hiện tại của xe khác với hướng cần đi tiếp theo, Pi 5 gửi lệnh `TURN` góc rẽ tương ứng.
   - Khi nhận phản hồi rẽ xong (`TURN_DONE`) từ ESP32, Pi 5 chờ ổn định quán tính 0.5s rồi mới gửi lệnh `MOVE` đi thẳng.
   - Nhằm tối ưu hóa hành trình, bộ điều khiển Pi 5 tự động gộp các ô đi thẳng liên tục trên cùng một đường thẳng thành một lệnh `MOVE` dài kèm theo tọa độ ô đích cần tới, giúp giảm tối đa số lần gửi lệnh.

### Lệnh chạy trên Pi 5:
```bash
python3 pi5_main.py --broker [IP_Broker_Laptop] --port /dev/ttyUSB0 --baud 115200
```
- `--broker`: Địa chỉ IP của Laptop chạy MQTT broker (Mặc định: `192.168.2.9`).
- `--port`: Cổng serial cắm cáp kết nối ESP32 (Mặc định: `/dev/ttyUSB0` trên Linux, `COMx` trên Windows).
- `--baud`: Tốc độ truyền baudrate (Mặc định: `115200`).
