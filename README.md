# 🤖 HỆ THỐNG XE TỰ HÀNH AMR & MÔ PHỎNG SONG HÀNH (DIGITAL TWIN)

> **Báo cáo môn học / Đồ án phát triển hệ thống xe tự hành AMR (Automated Mobile Robot)**
> Hệ thống tích hợp mô phỏng đồ họa thời gian thực (Pygame), truyền thông mạng không dây (MQTT), và điều khiển chuyển động thực tế qua vi điều khiển ESP32-S3 sử dụng xung phản hồi (Encoder) để đồng bộ hóa.

---

## 📌 Tổng Quan Hệ Thống

Dự án phát triển một mô hình **Automated Mobile Robot (AMR)** chạy thực tế đồng bộ song hành với một mô hình **Digital Twin** trên máy tính. Hệ thống cho phép:
1. **Mô phỏng đồ họa 2D:** Trên máy tính sử dụng thư viện Pygame, hiển thị bản đồ dạng lưới ô vuông (Grid Map), cho phép cấu hình kích thước vật lý, chỉnh sửa bản đồ động (Map Editor) và đa điểm đích (Multi-Waypoints).
2. **Thuật toán dẫn đường nâng cao:** Trực quan hóa và so sánh hiệu năng của 6 giải thuật tìm đường thông minh bao gồm cả cổ điển, bầy đàn và học tăng cường:
   
   * **BFS (Breadth-First Search - Tìm kiếm theo chiều rộng):**
     - *Nguyên lý:* Khám phá bản đồ theo từng tầng đồng tâm bằng cấu trúc hàng đợi Queue (FIFO). Khảo sát tất cả các ô láng giềng ở khoảng cách $k$ bước trước khi tiến ra khoảng cách $k+1$.
     - *Tính tối ưu:* Đảm bảo tìm ra đường đi ngắn nhất (tối ưu số bước) trên bản đồ lưới không trọng số.
     - *Độ phức tạp:* $O(V + E)$ với $V$ là số ô trống và $E$ là số liên kết giữa các ô.
     - *Trực quan hóa:* Hiển thị vùng duyệt lan tỏa dạng sóng tròn đối xứng từ vị trí xe xuất phát.
   
   * **Dijkstra (Tìm đường đi ngắn nhất tối ưu):**
     - *Nguyên lý:* Sử dụng hàng đợi ưu tiên (Priority Queue / Min Heap) để luôn duyệt ô có tổng chi phí tích lũy từ điểm xuất phát nhỏ nhất trước.
     - *Tính tối ưu:* Đảm bảo tìm ra lộ trình ngắn nhất tuyệt đối, kể cả trên bản đồ có phân cấp trọng số chi phí di chuyển giữa các vùng.
     - *Độ phức tạp:* $O((V + E) \log V)$ nhờ cấu trúc Heap.
     - *Trực quan hóa:* Loang mở rộng vùng biên thăm dò phụ thuộc vào hình dạng chướng ngại vật.
   
   * **Q-Learning (AI Học Tăng Cường - Reinforcement Learning):**
     - *Nguyên lý:* Đại diện cho trường phái AI tự học thông qua cơ chế thử và sai (Trial-and-Error). Robot tự di chuyển trên lưới bản đồ, nhận phần thưởng (Reward) để cập nhật ma trận giá trị hành vi Q-table $Q(s, a)$.
     - *Công thức Bellman cập nhật:*
       $$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ R + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]$$
       Trong đó: $\alpha = 0.3$ (learning rate), $\gamma = 0.9$ (discount factor). Thiết lập phần thưởng: Về đích: $+100$, Mỗi bước đi: $-1$, Va vào tường: $-10$.
     - *Cơ chế khám phá:* Huấn luyện qua 600 Episodes, sử dụng chính sách $\epsilon$-greedy giảm dần độ khám phá từ $1.0$ về $0.05$ để chuyển dần sang khai thác hành vi tối ưu đã học.
     - *Trực quan hóa:* Bản đồ nhiệt (Heatmap) biểu thị giá trị Q-value tốt nhất tại mỗi ô lưới, vẽ nên dòng chảy hành vi hướng về đích.
   
   * **Greedy Best-First Search (Tìm kiếm tham lam):**
     - *Nguyên lý:* Sử dụng hàm Heuristic ước lượng khoảng cách Manhattan tới đích để quyết định hướng đi:
       $$h(n) = |r_n - r_{goal}| + |c_n - c_{goal}|$$
       Thuật toán luôn ưu tiên đi vào ô có khoảng cách Manhattan ngắn nhất đến Goal tại mỗi bước duyệt.
     - *Ưu/Nhược điểm:* Tốc độ tính toán cực kỳ nhanh và hướng thẳng về đích. Tuy nhiên, dễ bị mắc kẹt vào các chướng ngại vật dạng túi (hình chữ U) và không đảm bảo tìm được đường đi ngắn nhất toàn cục.
     - *Trực quan hóa:* Vùng duyệt phát triển thành dải hẹp hướng thẳng về đích.
   
   * **GWF (Gradient Wavefront Field - Thuật toán động tự thiết kế):**
     - *Nguyên lý:* Giải thuật lai kết hợp giữa lập kế hoạch toàn cục và phản xạ tránh vật cản cục bộ:
       - **Pha 1 (Dựng trường thế năng):** Lan truyền ngược bằng BFS từ Goal ra toàn bản đồ. Ô Goal có thế năng $cost = 0$, các ô xa hơn tăng dần thế năng $+1$ đơn vị.
       - **Pha 2 (Bám Gradient):** Tại vị trí hiện tại, robot đọc cảm biến xung quanh, tìm ô láng giềng có thế năng nhỏ nhất để di chuyển vào (leo dốc thế năng đi xuống).
     - *Ưu điểm vượt trội:* Cực kỳ phù hợp cho ứng dụng thực tế. Khi gặp vật cản phát sinh, chỉ cần chạy lại BFS từ Goal với độ phức tạp tuyến tính cực nhanh $O(V)$ để cập nhật trường thế năng, thay vì phải chạy lại hàng đợi ưu tiên từ đầu như Dijkstra.
     - *Trực quan hóa:* Hiển thị số thế năng hoặc màu sắc phân cấp mức độ khoảng cách loang từ Goal ra toàn bộ lưới.
   
   * **ACO (Ant Colony Optimization - Trí tuệ bầy đàn):**
     - *Nguyên lý:* Mô phỏng hành vi bầy kiến tìm kiếm thức ăn. Kiến di chuyển ngẫu nhiên và để lại dấu vết hóa học Pheromone ($\tau$). Các con kiến sau sẽ lựa chọn hướng đi theo xác suất tỷ lệ thuận với lượng pheromone tích lũy.
     - *Công thức xác suất chọn ô tiếp theo:*
       $$p_{i, j} = \frac{[\tau_j]^\alpha \cdot [\eta_j]^\beta}{\sum_k [\tau_k]^\alpha \cdot [\eta_k]^\beta}$$
       Trong đó: $\eta_j = \frac{1}{\text{Manhattan}(j, goal) + 1}$ (thông tin Heuristic), $\alpha = 1.2$, $\beta = 2.5$.
     - *Cơ chế bay hơi và gia cường:* Sau mỗi vòng lặp (gồm 25 kiến), pheromone bay hơi với tốc độ $\rho = 0.25$ để tránh kẹt cực trị địa phương: $\tau \leftarrow \tau \cdot (1 - \rho)$. Đường đi ngắn nhất của kiến về đích sẽ được gia cường thêm pheromone: $\Delta \tau = \frac{100}{\text{độ dài đường}}$.
     - *Trực quan hóa:* Bản đồ nhiệt Pheromone hiển thị rõ nét con đường mòn tối ưu được bồi đắp bởi bầy kiến qua 60 thế hệ.
3. **Đồng bộ hóa thời gian thực (Digital Twin):** Kết nối không dây thông qua giao thức **MQTT**, gửi tọa độ di chuyển nội suy từ ESP32 lên Raspberry Pi 5 và hiển thị mượt mà trên giao diện máy tính.

---

## 🏗️ Kiến Trúc Hệ Thống

Kiến trúc liên kết 3 tầng (Laptop GUI - Pi 5 Controller - ESP32 Firmware):

```mermaid
graph TD
    subgraph Laptop (Digital Twin & Pathfinding)
        GUI[Pygame Interface] <--> LaptopMQTT[Laptop MQTT Client]
    end

    subgraph Raspberry Pi 5 (Central Controller)
        Pi5MQTT[Pi5 MQTT Client] <--> Pi5Ctrl[Pi5 Controller Logic]
        Pi5Ctrl <--> Pi5Serial[Pi5 Serial Driver]
    end

    subgraph ESP32-S3 (Motion Hardware)
        ESP32Serial[ESP32 Serial Listener] <--> ESP32Ctrl[ESP32 Main Loop]
        ESP32Ctrl -->|PWM Control| L298N[L298N Motor Driver]
        L298N -->|Voltage| Motors[4x DC Motors]
        Encoders[4x Incremental Encoders] -->|Pulse Interrupts| ESP32Ctrl
        ESP32Ctrl -->|I2C Display| LCD[LCD 1602 Display]
    end

    LaptopMQTT <-->|Wi-Fi / MQTT| Pi5MQTT
    Pi5Serial <-->|USB Cable / UART Serial| ESP32Serial
```

---

## 📡 Giao Thức Truyền Thông

### 1. Tầng Mạng (Wi-Fi MQTT): Laptop ↔ Raspberry Pi 5
Giao thức định dạng gói tin **JSON**, phân phối qua các topic:
* `amr/path` (QoS 1): Laptop gửi chuỗi tọa độ lộ trình `{"path": [[1,1], [1,2], [2,2]]}` xuống Pi 5.
* `amr/position` (QoS 0): Pi 5 cập nhật tọa độ thực thời gian thực `{"row": 1.25, "col": 1.0, "heading": 90}` để làm mượt chuyển động xe ảo trên Laptop.
* `amr/status` (QoS 0): Cập nhật trạng thái hoạt động (`IDLE`, `MOVING`, `ARRIVED`, `ERROR`).
* `amr/command` (QoS 1): Gửi lệnh điều khiển khẩn cấp hoặc Reset vị trí từ Laptop (`STOP`, `RESET`).
* `amr/config` (QoS 1): Đồng bộ cấu hình vật lý như kích thước ô bản đồ (`cell_mm`).

### 2. Tầng Vật Lý (Serial UART): Raspberry Pi 5 ↔ ESP32-S3
Kết nối vật lý thông qua cáp USB-to-UART với baudrate **115200**. Gói tin gửi nhận dạng chuỗi JSON kết thúc bằng ký tự xuống dòng `\n`:
* **Lệnh gửi xuống ESP32:**
  - Đi thẳng: `{"cmd": "MOVE", "heading": 90, "speed": 160, "row": 2, "col": 1}`
  - Rẽ tại chỗ: `{"cmd": "TURN", "angle": -90}` (Xoay góc âm là xoay trái, góc dương là xoay phải)
  - Dừng/Reset: `{"cmd": "STOP"}` / `{"cmd": "RESET", "row": 1, "col": 1, "heading": 90}`
* **Phản hồi từ ESP32 lên Pi 5:**
  - Hoàn thành đi 1 chặng: `{"ack": "DONE", "node": [2,1]}`
  - Hoàn thành rẽ hướng: `{"ack": "TURN_DONE", "heading": 0}`
  - Cập nhật vị trí trung gian: `{"pos": [1.45, 1.0]}` (Truyền với tần số 10Hz để vẽ mượt)

---

## 📂 Bố Trí Thư Mục Dự Án

```text
BTL_LTNC_AMR/
├── amr_project/                 # Mã nguồn Python chạy trên Laptop & Pi 5
│   ├── component/               # Các khối chức năng ảo của robot
│   │   ├── actuator.py          # Bộ điều hướng dịch chuyển mượt xe ảo
│   │   ├── processor.py         # Bộ xử lý trung tâm và tích hợp thuật toán tìm đường
│   │   └── sensor.py            # Cảm biến quét lưới ô vuông phát hiện vật cản
│   ├── core/                    # Lớp điều khiển chính của simulator
│   │   ├── amr.py               # Định nghĩa thực thể xe ảo (kích thước, vị trí, góc vẽ)
│   │   ├── animator.py          # Bộ tạo hiệu ứng trực quan hóa các bước duyệt của thuật toán
│   │   ├── application.py       # Quản lý vòng lặp đồ họa Pygame, màn hình cài đặt và MQTT
│   │   ├── graphic.py           # Vẽ lưới bản đồ, xe, nhãn thông tin và HUD panel
│   │   ├── input.py             # Lắng nghe sự kiện chuột, bàn phím điều khiển
│   │   ├── map.py               # Khởi tạo ma trận bản đồ, tạo bản đồ ngẫu nhiên
│   │   ├── map_editor.py        # Cho phép vẽ/xóa chướng ngại vật bằng chuột, tạo mê cung tự động
│   │   └── waypoint_manager.py  # Quản lý danh sách các điểm đích cần đi qua liên tục
│   ├── network/                 # Thư viện truyền thông không dây
│   │   ├── laptop_mqtt.py       # MQTT Client chạy ngầm trên Laptop
│   │   ├── pi5_mqtt.py          # MQTT Client chạy ngầm trên Raspberry Pi 5
│   │   ├── pi5_serial.py        # Driver giao tiếp UART Serial kết nối với ESP32
│   │   └── protocol.py          # Định nghĩa cấu trúc gói tin và topic dùng chung
│   ├── utils/                   # Hàm phụ trợ tính toán chuyển đổi tọa độ
│   │   └── utils.py             # Chuyển đổi qua lại giữa tọa độ ô và tọa độ pixel màn hình
│   ├── main.py                  # Điểm khởi chạy chương trình chính thức (Laptop GUI)
│   └── pi5_main.py              # Script điều khiển chạy trên Raspberry Pi 5
├── esp32_firmware/              # Mã nguồn C/C++ chạy trên vi điều khiển ESP32-S3
│   └── AMR_Firmware/            # Thư mục chứa project Arduino IDE
│       ├── AMR_Firmware.ino     # Luồng hoạt động chính, đọc Encoder, điều khiển PWM động cơ
│       ├── cell_config.h        # Quản lý cấu hình động kích thước ô bản đồ (mm) nhận qua Serial
│       ├── config.h             # Định nghĩa sơ đồ chân (Pinout) và thông số cơ học GA25
│       └── lcd_display.h        # Driver điều khiển màn hình LCD 1602 I2C
└── maps/                        # Thư mục lưu trữ dữ liệu bản đồ dưới dạng JSON
```

---

## ⚡ Hướng Dẫn Cài Đặt Nhanh

### 1. Chuẩn Bị Môi Trường Laptop
Yêu cầu hệ điều hành cài đặt sẵn Python 3.10+. Tiến hành cài đặt các thư viện cần thiết:
```bash
pip install pygame paho-mqtt
```

### 2. Khởi Động Broker MQTT
Hệ thống sử dụng Mosquitto broker làm trung gian kết nối. Cần cài đặt và chạy dịch vụ Mosquitto trên Laptop hoặc Raspberry Pi 5.
* **Trên Windows:** Chạy dịch vụ Mosquitto qua Command Prompt (quyền Admin):
  ```cmd
  net start mosquitto
  ```
* **Mẹo cấu hình:** Đảm bảo file cấu hình `mosquitto.conf` cho phép kết nối từ bên ngoài bằng cách thêm:
  ```text
  listener 1883 0.0.0.0
  allow_anonymous true
  ```

### 3. Vận Hành Mô Phỏng Song Hành

1. **Khởi chạy giao diện chính trên Laptop:**
   ```bash
   python amr_project/main.py --broker [IP_MQTT_BROKER]
   ```
   *(Ví dụ: `python amr_project/main.py --broker 192.168.1.15`)*

2. **Chạy trình điều khiển Pi 5 (nếu kết nối xe thực):**
   ```bash
   python amr_project/pi5_main.py --broker [IP_MQTT_BROKER] --port /dev/ttyUSB0
   ```

3. **Nạp code ESP32:** Mở thư mục `esp32_firmware/AMR_Firmware` bằng Arduino IDE, cài đặt thư viện `ArduinoJson` và `LiquidCrystal_I2C`, sau đó tiến hành nạp xuống board ESP32-S3.

---

## 🎮 Hướng Dẫn Điều Khiển Trên Giao Diện Laptop

Khi chạy giao diện Pygame, bạn có thể tương tác nhanh thông qua các thao tác:
* **Chuột Trái:** Vẽ hoặc xóa chướng ngại vật (Tường màu đỏ).
* **Chuột Phải:** Đặt vị trí đích đến (**Goal** - hình tròn cam).
* **Ctrl + Chuột Phải:** Đặt danh sách đa điểm đích (khi bật chế độ Waypoint Mode).
* **Phím SPACE:** Chạy thuật toán tìm đường đi ngắn nhất từ vị trí xe hiện tại đến đích.
* **Phím ENTER:** Gửi lộ trình đi xuống xe thực (qua MQTT) hoặc kích hoạt xe ảo di chuyển từng bước.
* **Phím A:** Kích hoạt chế độ di chuyển tự động (Auto-run) liên tục không dừng cho đến đích.
* **Phím R:** Reset robot ảo và robot thực về vị trí xuất phát mặc định `(1,1)`.
* **Phím N:** Tự động tạo ngẫu nhiên một bản đồ mới có mật độ vật cản 18%.
* **Phím E:** Bật/Tắt chế độ vẽ bản đồ nhanh (Map Editor), nhấn giữ chuột trái để quét tường, chuột phải để xóa tường.
* **Phím W:** Bật/Tắt chế độ đi qua đa điểm đích (Waypoint Mode).
* **Phím F:** Bật/Tắt hiển thị bản đồ trường thế năng / khoảng cách (Cost Field) của thuật toán.
* **Phím Z:** Chạy hiệu ứng trực quan hóa (Animation) từng bước duyệt của thuật toán tìm đường.
* **Phím ESC:** Quay trở lại màn hình cấu hình kích thước lưới bản đồ.
* **Phím số 1 đến 6:** Chuyển đổi nhanh giữa các thuật toán tìm đường:
  1. *BFS*
  2. *Dijkstra*
  3. *Q-Learning (RL)*
  4. *Greedy*
  5. *GWF (Tu thiet ke)*
  6. *ACO (Ant Colony)*
