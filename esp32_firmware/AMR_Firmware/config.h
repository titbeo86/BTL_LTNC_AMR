// ═══════════════════════════════════════════════════
//  config.h — Cấu hình ESP32-S3 AMR
//  Pinout THỰC TẾ theo phần cứng đã đấu dây
//  GA25 280RPM + Mecanum 52mm + HC-SR04
// ═══════════════════════════════════════════════════
#pragma once

// ── MOTOR PINS (L298N #1 — 2 bánh trái) ───────────
#define MOTOR_A_IN1   6    // Đảo ngược thứ tự đầu cắm (6, 5, 4)
#define MOTOR_A_IN2   5
#define MOTOR_A_EN    4
#define MOTOR_B_IN1   7    // Motor B (trên-trái) — xác nhận thực tế
#define MOTOR_B_IN2   9
#define MOTOR_B_EN    10

// ── MOTOR PINS (L298N #2 — 2 bánh phải) ───────────
// Pin giữ nguyên gốc, KHÔNG đảo IN1/IN2. 
// Phần cứng đã đấu chuẩn, PWM dương = tiến.
#define MOTOR_C_IN1   40   // Đảo ngược thứ tự đầu cắm (40, 39, 38)
#define MOTOR_C_IN2   39   
#define MOTOR_C_EN    38
#define MOTOR_D_IN1   41   // Trả lại 41
#define MOTOR_D_IN2   42   // Trả lại 42
#define MOTOR_D_EN    2

// ── ENCODER PINS (GIỐNG test_hardware.ino) ───────
#define ENC_A1   17   // Motor A kênh 1
#define ENC_A2   18   // Motor A kênh 2
#define ENC_B1   8    // Motor B kênh 1
#define ENC_B2   11   // Motor B kênh 2
#define ENC_C1   1    // Motor C kênh 1 (GIỮ NGUYÊN GỐC)
#define ENC_C2   48   // Motor C kênh 2
#define ENC_D1   21   // Motor D kênh 1 (GIỮ NGUYÊN GỐC)
#define ENC_D2   47   // Motor D kênh 2

// ── I2C BUS (LCD) ────────────────────────────────
#define I2C_SDA   13
#define I2C_SCL   12   // [JTAG MTDO - vẫn dùng OK]
#define LCD_ADDR      0x27   // Thử 0x3F nếu không thấy


// ── SERIAL UART → Pi5 ────────────────────────────
// LƯU Ý: Kết nối qua cổng USB chính (USB-to-COM), không dùng GPIO1/2 rời
// Pi5 thấy ESP32 như 1 cổng /dev/ttyUSB0 hoặc /dev/ttyACM0
// Dùng Serial (USB CDC) thay vì Serial1/HardwareSerial riêng
#define PI5_BAUD  115200

// ── LEDC PWM CONFIG ──────────────────────────────
#define PWM_FREQ      1000
#define PWM_BITS      8
#define PWM_CH_A      0
#define PWM_CH_B      1
#define PWM_CH_C      2
#define PWM_CH_D      3

// ── CƠ HỌC GA25 280RPM + MECANUM 52mm ───────────
#define ENCODER_PPR        234       // Đo thực tế theo tỷ số truyền 21.3
#define WHEEL_DIAMETER_MM  52.0f
#define MM_PER_TICK        0.7093f    // Hiệu chuẩn thực tế từ đo đạc chạy thẳng 10 ô (63.5cm khi đặt 25cm)
#define ROBOT_DIAMETER_MM  258.5f    // Hiệu chuẩn thực tế từ đo đạc rẽ 90 độ (quay 48 độ) và 180 độ (quay 95 độ)

// ── KÍCH THƯỚC Ô — THAY ĐỔI ĐƯỢC ─────────────────
#define CELL_SIZE_MM_DEFAULT  200
// Giá trị tham khảo (đo lại bằng calibrate_cell.ino):
#define MOVE_TICKS_150  1374
#define MOVE_TICKS_200  1832
#define MOVE_TICKS_250  2289
#define MOVE_TICKS_300  2747

// ── PID THAM SỐ — Hiệu chỉnh bằng thuật toán ──
#define PID_KP    0.5f       // Hệ số tỷ lệ (Proportional)
#define PID_KI    0.2f       // Hệ số tích phân (Integral) - Tích lũy sai số theo thời gian
#define PID_KD    0.00f      // Hệ số vi phân (Derivative) - Không dùng cho vận tốc
#define PID_OUT_MAX   255
#define PID_OUT_MIN  -255

// ── ĐIỀU KHIỂN DI CHUYỂN ─────────────────────────
#define MOVE_SPEED_DEFAULT  250  // Tốc độ vận hành tối ưu (Khắc phục Deadband vật lý)



// ── TIMING ───────────────────────────────────────
#define PID_LOOP_MS       10
#define LCD_UPDATE_MS    500
#define SERIAL_TIMEOUT_MS 60000    // 60 giây — tránh timeout giả khi đi thẳng dài

// ── HÀM TIỆN ÍCH ─────────────────────────────────
inline long cellMM_to_ticks(int mm) {
    return (long)((float)mm / MM_PER_TICK);
}
