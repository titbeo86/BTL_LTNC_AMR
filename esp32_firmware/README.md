# ⚡ FIRMWARE ĐIỀU KHIỂN ĐỘNG CƠ AMR (ESP32-S3)

Thư mục này chứa mã nguồn **C/C++** (chạy trên vi điều khiển ESP32-S3) chịu trách nhiệm điều khiển trực tiếp 4 động cơ DC, đọc phản hồi vòng lặp kín từ Encoder và tương tác với màn hình hiển thị LCD 1602.

---

## 🔌 1. Sơ Đồ Đấu Nối Phần Cứng (Pinout)

Dựa trên cấu hình thực tế trong tệp [config.h](file:///C:/Users/Admin/Downloads/BTL_LTNC_AMR/esp32_firmware/AMR_Firmware/config.h), sơ đồ chân kết nối của ESP32-S3 được bố trí cụ thể như sau:

### Động Cơ DC (Điều Khiển Qua L298N)
Hệ thống sử dụng hai mạch cầu H L298N để điều khiển độc lập hướng và tốc độ quay (qua tín hiệu PWM tần số 20kHz, độ phân giải 8-bit) của 4 bánh xe:

| Động Cơ | Vị Trí | Chân IN1 | Chân IN2 | Chân EN (PWM) | Kênh PWM LEDC |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Motor A** | Trên - Trái | GPIO 6 | GPIO 5 | GPIO 4 | Kênh 0 |
| **Motor B** | Dưới - Trái | GPIO 7 | GPIO 9 | GPIO 10 | Kênh 1 |
| **Motor C** | Trên - Phải | GPIO 40 | GPIO 39 | GPIO 38 | Kênh 2 |
| **Motor D** | Dưới - Phải | GPIO 41 | GPIO 42 | GPIO 2 | Kênh 3 |

### Ngắt Encoder Động Cơ
Đọc phản hồi xung tốc độ cao bằng cách cấu hình chân Encoder 1 làm chân ngắt cạnh lên (`RISING`) và chân Encoder 2 làm chân đọc chiều quay:

* **Motor A (Kênh ngắt 1/2):** GPIO 17 / GPIO 18
* **Motor B (Kênh ngắt 1/2):** GPIO 8 / GPIO 11
* **Motor C (Kênh ngắt 1/2):** GPIO 1 / GPIO 48
* **Motor D (Kênh ngắt 1/2):** GPIO 21 / GPIO 47

### Màn Hình LCD 1602 (Giao Tiếp I2C)
* **SDA (Data Line):** GPIO 13
* **SCL (Clock Line):** GPIO 12
* **Địa chỉ I2C:** `0x27` (hoặc `0x3F`)

---

## ⚙️ 2. Hiệu Chuẩn Cơ Học & Đếm Xung Encoder

Để đảm bảo xe chạy thẳng chính xác theo khoảng cách cài đặt và xoay góc đúng mong muốn, các hệ số cơ học của xe GA25 đã được đo đạc hiệu chuẩn thực tế:

* **Động cơ GA25 280RPM:** Tỷ số truyền 21.3, xung phản hồi danh định là **234 PPR** (xung/vòng).
* **Đường kính bánh xe:** **52.0 mm**.
* **Độ dịch chuyển thực tế:** Hiệu chuẩn từ thực nghiệm đo đạc chạy thẳng 10 ô thực tế cho ra hệ số chuyển đổi chính xác: **0.7093 mm/tick**.
* **Đường kính quay vòng của robot:** Hiệu chuẩn rẽ xoay 90 độ và 180 độ thực tế cho ra thông số khoảng cách bánh xe: **258.5 mm**.

### Hàm Chuyển Đổi Khoảng Cách Sang Xung Encoder:
```cpp
inline long cellMM_to_ticks(int mm) {
    return (long)((float)mm / MM_PER_TICK);
}
```

---

## 🧠 3. Giải Thích Luồng Xử Lý Chính Trong Firmware

1. **Ngắt Đọc Xung Tốc Độ Cao (`isrEnc`):**
   - 4 động cơ sử dụng 4 hàm phục vụ ngắt (`isrEncA`, `isrEncB`, `isrEncC`, `isrEncD`) được định vị trên bộ nhớ IRAM tốc độ cao (`IRAM_ATTR`).
   - Mỗi khi chân Encoder 1 có xung cạnh lên, ngắt kích hoạt lập tức đọc chân Encoder 2 để tăng hoặc giảm số xung thực tế dựa trên chiều quay.
2. **Nội Suy Tọa Độ Thực Để Đồng Bộ Hóa Xe Ảo (`_getCurrentPosFloat`):**
   - Trong quá trình xe chạy thẳng từ ô xuất phát sang ô kế tiếp, ESP32 liên tục tính tỷ lệ: `Đã đi (ticksMoved) / Cần đi (targetTicks)`.
   - Hệ số tỷ lệ này nhân với hướng di chuyển (`dirRow`, `dirCol`) cộng dồn vào tọa độ ô ban đầu để tạo ra tọa độ số thực (float) liên tục (ví dụ: `1.45, 1.0` thay vì nhảy bước từ `1` sang `2`).
   - Tọa độ số thực này được đóng gói JSON và gửi qua cổng Serial lên Raspberry Pi 5 với chu kỳ **100ms** (10Hz).
3. **Cơ Chế Bảo Vệ Timeout Phần Cứng:**
   - Trong vòng lặp `loop()`, nếu xe đang di chuyển hoặc xoay hướng mà không nhận được bất kỳ cập nhật nào mới từ Pi 5 hoặc bị kẹt bánh không thể tăng xung quá **60 giây** (`SERIAL_TIMEOUT_MS`), hệ thống tự động tắt toàn bộ động cơ (`_stopAll()`) và phát tín hiệu báo lỗi `{"ack":"ERROR","msg":"TIMEOUT"}` để bảo vệ động cơ khỏi quá dòng, chập cháy.
