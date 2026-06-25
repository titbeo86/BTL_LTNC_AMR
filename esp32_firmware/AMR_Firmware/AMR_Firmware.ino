// ═════════════════════════════════════════════════════════════════════════════
//  AMR_Firmware.ino — Firmware điều khiển chính trên vi điều khiển ESP32-S3
//  ĐỒ ÁN PHÁT TRIỂN XE TỰ HÀNH AMR (AUTOMATED GUIDED VEHICLE)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  MÔ TẢ LUỒNG HOẠT ĐỘNG:
//    - Nhận lệnh điều khiển dạng JSON từ Raspberry Pi 5 thông qua cổng Serial.
//    - Đọc dữ liệu phản hồi từ 4 ngắt Encoder gắn trên 4 động cơ DC.
//    - Tính toán vị trí trung gian chính xác dạng số thực (float) để vẽ robot ảo.
//    - Điều khiển động cơ trực tiếp thông qua tín hiệu số GPIO và bộ tạo xung PWM.
//    - Cập nhật trạng thái hiển thị thời gian thực lên màn hình LCD I2C.
// ═════════════════════════════════════════════════════════════════════════════

#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include "driver/gpio.h"

#include "config.h"
#include "cell_config.h"
#include "lcd_display.h"

// Định nghĩa cổng giao tiếp Serial kết nối với Raspberry Pi 5
#define Pi5Serial Serial

// Khai báo đối tượng màn hình hiển thị LCD I2C
LCDDisplay lcd;

// ── CÁC BIẾN TOÀN CỤC LƯU TRỮ VÀ ĐẾM XUNG ENCODER ────────────────────────────
// Sử dụng từ khóa volatile để trình biên dịch không tối ưu hóa biến này,
// đảm bảo dữ liệu luôn được cập nhật chính xác từ trong chương trình phục vụ ngắt (ISR).
volatile long encA = 0, encB = 0, encC = 0, encD = 0;

// Các hàm phục vụ ngắt (Interrupt Service Routine - ISR) cho 4 kênh Encoder
// Được lưu trữ trên bộ nhớ IRAM tốc độ cao để đảm bảo tốc độ phản hồi ngắt tức thì.
void IRAM_ATTR isrEncA() { if (digitalRead(ENC_A2)) encA++; else encA--; }
void IRAM_ATTR isrEncB() { if (digitalRead(ENC_B2)) encB++; else encB--; }
void IRAM_ATTR isrEncC() { if (digitalRead(ENC_C2)) encC++; else encC--; }
void IRAM_ATTR isrEncD() { if (digitalRead(ENC_D2)) encD++; else encD--; }

// ── HÀM ĐIỀU KHIỂN ĐỘNG CƠ TRỰC TIẾP QUA GPIO VÀ PWM ─────────────────────────
// Tham số: Chân IN1, IN2 xác định chiều quay; Chân EN cấp xung PWM xác định tốc độ.
void setMotor(int in1, int in2, int enPin, int pwm) {
    if (pwm > 0) {
        digitalWrite(in1, HIGH); digitalWrite(in2, LOW); // Quay thuận
    } else if (pwm < 0) {
        digitalWrite(in1, LOW); digitalWrite(in2, HIGH); // Quay ngược
    } else {
        digitalWrite(in1, LOW); digitalWrite(in2, LOW);  // Phanh thả trôi chủ động (Tránh rò điện làm tự quay bánh)
    }
    ledcWrite(enPin, min(abs(pwm), 255)); // Áp đặt giá trị tốc độ qua kênh PWM tương ứng
}

// Hàm dừng khẩn cấp toàn bộ 4 động cơ
void stopAllMotors() {
    digitalWrite(MOTOR_A_IN1, LOW); digitalWrite(MOTOR_A_IN2, LOW); ledcWrite(MOTOR_A_EN, 0);
    digitalWrite(MOTOR_B_IN1, LOW); digitalWrite(MOTOR_B_IN2, LOW); ledcWrite(MOTOR_B_EN, 0);
    digitalWrite(MOTOR_C_IN1, LOW); digitalWrite(MOTOR_C_IN2, LOW); ledcWrite(MOTOR_C_EN, 0);
    digitalWrite(MOTOR_D_IN1, LOW); digitalWrite(MOTOR_D_IN2, LOW); ledcWrite(MOTOR_D_EN, 0);
}

// Lệnh đi thẳng: Cả 4 bánh xe cùng quay tiến với giá trị tốc độ PWM giống nhau.
void driveForward(int pwm) {
    setMotor(MOTOR_A_IN1, MOTOR_A_IN2, MOTOR_A_EN, pwm);
    setMotor(MOTOR_B_IN1, MOTOR_B_IN2, MOTOR_B_EN, pwm);
    setMotor(MOTOR_C_IN1, MOTOR_C_IN2, MOTOR_C_EN, pwm);
    setMotor(MOTOR_D_IN1, MOTOR_D_IN2, MOTOR_D_EN, pwm);
}

// Lệnh rẽ tại chỗ (Tank turn): Cụm bánh bên trái (AB) và bên phải (CD) quay ngược chiều nhau.
void driveTurn(int leftPwm, int rightPwm) {
    setMotor(MOTOR_A_IN1, MOTOR_A_IN2, MOTOR_A_EN, leftPwm);
    setMotor(MOTOR_B_IN1, MOTOR_B_IN2, MOTOR_B_EN, leftPwm);
    setMotor(MOTOR_C_IN1, MOTOR_C_IN2, MOTOR_C_EN, rightPwm);
    setMotor(MOTOR_D_IN1, MOTOR_D_IN2, MOTOR_D_EN, rightPwm);
}

// ── CẤU TRÚC LƯU TRỮ TRẠNG THÁI HỆ THỐNG ─────────────────────────────────────
struct State {
    int  row = 1, col = 1;          // Tọa độ node hiện tại trên bản đồ (mặc định xuất phát 1,1)
    int  heading = 90;              // Hướng mặt hiện tại (90=Tiến/Bắc, 0=Phải/Đông, 270=Lùi/Nam, 180=Trái/Tây)
    int  targetHeading = 90;        // Hướng mặt đích cần quay tới

    bool moving     = false;        // Cờ trạng thái xe đang đi thẳng
    bool turning    = false;        // Cờ trạng thái xe đang xoay hướng
    int  moveSpeed  = 200;          // Tốc độ PWM chạy thẳng mặc định (Đã tối ưu thực tế)
    long targetTicks = 0;           // Tổng số lượng xung Encoder mục tiêu của hành trình hiện tại
    long ticksMoved  = 0;           // Số lượng xung Encoder trung bình thực tế xe đã đi được

    int  stepDone  = 0;             // Tổng số bước (số ô) đã hoàn thành
    const char* dirName = "IDLE";   // Tên chuỗi trạng thái hoạt động hiển thị trên màn hình LCD
    
    int  turnDir = 1;               // Hướng xoay: +1 = xoay phải (Clockwise), -1 = xoay trái (Counter-clockwise)

    unsigned long lastCmdMs = 0;    // Thời điểm cuối cùng nhận lệnh (dùng để giám sát lỗi timeout)
    float currentPwm = 0.0f;        // Tốc độ PWM thực tế đang áp đặt xuống động cơ
} state;

int _nextRow = 1, _nextCol = 1;     // Tọa độ ô kế tiếp trong chặng di chuyển hiện tại

// Chuyển góc hướng mặt xe thành chuỗi text hiển thị trên LCD
const char* _headingName(int h) {
    switch(h) {
        case 90:  return "TIEN";
        case 270: return "LUI";
        case 0:   return "PHAI";
        case 180: return "TRAI";
        default:  return "---";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  KHỞI TẠO HỆ THỐNG (SETUP)
// ─────────────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println("\n[ESP32] AMR Firmware v2 (Direct GPIO) khoi dong...");

    // Cấu hình các chân điều khiển động cơ là OUTPUT
    int motorPins[] = {
        MOTOR_A_IN1, MOTOR_A_IN2, MOTOR_A_EN,
        MOTOR_B_IN1, MOTOR_B_IN2, MOTOR_B_EN,
        MOTOR_C_IN1, MOTOR_C_IN2, MOTOR_C_EN,
        MOTOR_D_IN1, MOTOR_D_IN2, MOTOR_D_EN
    };
    for (int p : motorPins) { 
        gpio_reset_pin((gpio_num_t)p); // Giải phóng chân khỏi chức năng phụ (JTAG/USB) để tránh xung đột
        pinMode(p, OUTPUT); 
        digitalWrite(p, LOW); 
    }

    // Thiết lập kênh phát xung PWM độc lập cho từng động cơ để tránh nhiễu chéo tần số
    ledcAttachChannel(MOTOR_A_EN, 20000, 8, 0);
    ledcAttachChannel(MOTOR_B_EN, 20000, 8, 1);
    ledcAttachChannel(MOTOR_C_EN, 20000, 8, 2);
    ledcAttachChannel(MOTOR_D_EN, 20000, 8, 3);
    stopAllMotors();
    Serial.println("[ESP32] Motors OK (Direct GPIO)");

    // Cấu hình chân đọc xung Encoder là INPUT_PULLUP và gán ngắt cạnh lên (RISING)
    int encPins[] = {ENC_A1, ENC_A2, ENC_B1, ENC_B2,
                     ENC_C1, ENC_C2, ENC_D1, ENC_D2};
    for (int p : encPins) pinMode(p, INPUT_PULLUP);
    attachInterrupt(ENC_A1, isrEncA, RISING);
    attachInterrupt(ENC_B1, isrEncB, RISING);
    attachInterrupt(ENC_C1, isrEncC, RISING);
    attachInterrupt(ENC_D1, isrEncD, RISING);
    Serial.println("[ESP32] Encoders OK");

    // Khởi tạo màn hình LCD qua chuẩn giao tiếp I2C
    Wire.begin(I2C_SDA, I2C_SCL);
    lcd.begin();
    lcd.showMessage("AMR Ready v3", "Direct GPIO");

    Serial.println("[ESP32] San sang nhan lenh!");
}

// ── TÍNH TOÁN VỊ TRÍ TRUNG GIAN DẠNG SỐ NGUYÊN (CHO LCD) ──────────────────────
void _getCurrentPos(int &outRow, int &outCol) {
    outRow = state.row;
    outCol = state.col;
    if (state.moving) {
        long ticksPerCell = gCell.ticksPerCell;
        if (ticksPerCell > 0) {
            long cellsMoved = state.ticksMoved / ticksPerCell;
            int dirRow = (_nextRow > state.row) ? 1 : ((_nextRow < state.row) ? -1 : 0);
            int dirCol = (_nextCol > state.col) ? 1 : ((_nextCol < state.col) ? -1 : 0);
            outRow = state.row + cellsMoved * dirRow;
            outCol = state.col + cellsMoved * dirCol;
            if (dirRow > 0 && outRow > _nextRow) outRow = _nextRow;
            if (dirRow < 0 && outRow < _nextRow) outRow = _nextRow;
            if (dirCol > 0 && outCol > _nextCol) outCol = _nextCol;
            if (dirCol < 0 && outCol < _nextCol) outCol = _nextCol;
        }
    }
}

// ── TÍNH TOÁN VỊ TRÍ TRUNG GIAN DẠNG SỐ THỰC (ĐỒNG BỘ ROBOT ẢO) ──────────────
// Tính toán nội suy tọa độ thực tế dưới dạng số thực (float) dựa trên tỷ lệ
// xung Encoder đã dịch chuyển so với tổng xung cần thiết để di chuyển hết 1 ô bản đồ.
void _getCurrentPosFloat(float &outRow, float &outCol) {
    outRow = (float)state.row;
    outCol = (float)state.col;
    if (state.moving) {
        long ticksPerCell = gCell.ticksPerCell;
        if (ticksPerCell > 0) {
            float cellsMoved = (float)state.ticksMoved / (float)ticksPerCell;
            int dirRow = (_nextRow > state.row) ? 1 : ((_nextRow < state.row) ? -1 : 0);
            int dirCol = (_nextCol > state.col) ? 1 : ((_nextCol < state.col) ? -1 : 0);
            outRow = (float)state.row + cellsMoved * (float)dirRow;
            outCol = (float)state.col + cellsMoved * (float)dirCol;
            // Áp đặt giới hạn để tọa độ thực không vượt quá phạm vi ô đích mong muốn
            if (dirRow > 0 && outRow > _nextRow) outRow = (float)_nextRow;
            if (dirRow < 0 && outRow < _nextRow) outRow = (float)_nextRow;
            if (dirCol > 0 && outCol > _nextCol) outCol = (float)_nextCol;
            if (dirCol < 0 && outCol < _nextCol) outCol = (float)_nextCol;
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  VÒNG LẶP CHÍNH (LOOP)
// ─────────────────────────────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();

    // Tính toán và hiển thị tần số vòng lặp chẩn đoán (Loop Hz) lên Serial monitor
    static unsigned long lastFps = 0;
    static long loopCount = 0;
    loopCount++;
    if (now - lastFps >= 1000) {
        Serial.printf("[SYSTEM] Loop Hz: %ld\n", loopCount);
        loopCount = 0;
        lastFps = now;
    }

    // ── 1. Đọc và phân tích lệnh Serial từ Pi5 ──
    _readSerial();

    // ── 2. Bộ điều khiển Động cơ (Chạy chu kỳ 10ms ổn định) ──
    static unsigned long lastCtrl = 0;
    if (now - lastCtrl >= 10) {
        _controlMotors();
        lastCtrl = now;
    }

    // ── 3. Giám sát phản hồi hành trình từ Encoder ──
    _checkArrival();

    // ── 4. Cơ chế bảo vệ Timeout phần cứng ──
    // Nếu xe đang di chuyển/xoay mà không nhận thêm phản hồi hoặc bị kẹt quá 60s,
    // tiến hành dừng khẩn cấp để bảo vệ động cơ khỏi cháy chập.
    if ((state.moving || state.turning) &&
        (now > state.lastCmdMs) &&
        (now - state.lastCmdMs > 60000)) {
        _stopAll();
        Serial.println("[ESP32] TIMEOUT!");
        _sendRaw("{\"ack\":\"ERROR\",\"msg\":\"TIMEOUT\"}");
    }

    // ── 5. Cập nhật dữ liệu hiển thị LCD thời gian thực ──
    int displayRow, displayCol;
    _getCurrentPos(displayRow, displayCol);
    lcd.update(displayRow, displayCol, state.heading, state.dirName, state.stepDone);

    // ── 6. Gửi dữ liệu vị trí nội suy định kỳ lên Pi5 (100ms / 10Hz) ──
    static unsigned long lastPos = 0;
    if (now - lastPos >= 100) {
        _publishPosition();
        lastPos = now;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  ĐỌC VÀ GIẢI MÃ LỆNH TỪ RASPBERRY PI 5 (SERIAL JSON PARSER)
// ─────────────────────────────────────────────────────────────────────────────
void _readSerial() {
    if (!Pi5Serial.available()) return;

    String line = Pi5Serial.readStringUntil('\n');
    line.trim();
    if (line.isEmpty()) return;

    StaticJsonDocument<128> doc;
    if (deserializeJson(doc, line)) {
        Serial.println("[ESP32] JSON error: " + line);
        return;
    }

    const char* cmd = doc["cmd"];
    if (cmd == nullptr) return; // Tránh lỗi crash hệ thống nếu gói tin rỗng trường cmd
    
    state.lastCmdMs = millis();

    // 1. Nhận lệnh DI CHUYỂN (MOVE)
    if (strcmp(cmd, "MOVE") == 0) {
        int speed  = doc["speed"]  | 200;
        int newRow = doc["row"]    | state.row;
        int newCol = doc["col"]    | state.col;
        _startMove(speed, newRow, newCol);
    }
    // 2. Nhận lệnh DỪNG KHẨN CẤP (STOP)
    else if (strcmp(cmd, "STOP") == 0) {
        _stopAll();
        _sendRaw("{\"ack\":\"STOP\"}");
    }
    // 3. Nhận lệnh XOAY HƯỚNG (TURN)
    else if (strcmp(cmd, "TURN") == 0) {
        int angle = doc["angle"] | 90;
        _startTurn(angle);
    }
    // 4. Nhận gói tin PING mạng
    else if (strcmp(cmd, "PING") == 0) {
        _sendRaw("{\"ack\":\"PONG\"}");
    }
    // 5. Nhận cấu hình kích thước ô bản đồ (CELL) để cập nhật số xung tương ứng
    else if (strcmp(cmd, "CELL") == 0) {
        int mm = doc["mm"] | 200;
        gCell.setCellMM(mm);
        char buf[64];
        snprintf(buf, sizeof(buf), "{\"ack\":\"CELL_OK\",\"mm\":%d}", gCell.cellMM);
        _sendRaw(buf);
    }
    // 6. Nhận lệnh THIẾT LẬP LẠI TRẠNG THÁI (RESET) - Đồng bộ vị trí xuất phát mới
    else if (strcmp(cmd, "RESET") == 0) {
        _stopAll();
        state.row = doc["row"] | 1;
        state.col = doc["col"] | 1;
        int h = doc["heading"] | 90;
        state.heading = h;
        state.targetHeading = h;
        state.ticksMoved = 0;
        state.targetTicks = 0;
        state.stepDone = 0;
        encA = 0; encB = 0; encC = 0; encD = 0;
        char buf[80];
        snprintf(buf, sizeof(buf), "{\"ack\":\"RESET_OK\",\"row\":%d,\"col\":%d,\"heading\":%d}", state.row, state.col, state.heading);
        _sendRaw(buf);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  KHỞI ĐỘNG CHẶNG DI CHUYỂN THẲNG
// ─────────────────────────────────────────────────────────────────────────────
void _startMove(int speed, int nextRow, int nextCol) {
    if (state.moving || state.turning) return;

    state.moveSpeed    = speed;
    state.moving       = true;
    state.currentPwm   = 0;
    
    // Tính tổng số ô cần di chuyển trong chặng này
    int cells = abs(nextRow - state.row) + abs(nextCol - state.col);
    if (cells == 0) cells = 1;
    // Tính toán số xung mục tiêu dựa trên số ô và xung cấu hình của mỗi ô
    state.targetTicks  = (long)cells * gCell.ticksPerCell;
    state.ticksMoved   = 0;
    state.dirName      = "TIEN";

    // Khởi tạo lại toàn bộ bộ đếm xung trước khi chuyển động
    encA = 0; encB = 0; encC = 0; encD = 0;

    _nextRow = nextRow;
    _nextCol = nextCol;

    Serial.printf("[ESP32] MOVE speed=%d cells=%d ticks=%ld -> (%d,%d)\n",
                  speed, cells, state.targetTicks, nextRow, nextCol);
}

// ─────────────────────────────────────────────────────────────────────────────
//  KHỞI ĐỘNG CHẶNG XOAY HƯỚNG TẠI CHỖ (TANK TURN)
// ─────────────────────────────────────────────────────────────────────────────
void _startTurn(int angleDeg) {
    if (state.moving || state.turning) return;

    state.targetHeading = (state.heading + angleDeg + 360) % 360;
    state.turning       = true;
    state.currentPwm    = 0;
    
    // Tính toán chiều dài cung tròn quay của bánh xe và chuyển đổi sang xung encoder tương đương
    float arc_mm = (abs(angleDeg) / 360.0f) * (PI * ROBOT_DIAMETER_MM);
    state.targetTicks = (long)(arc_mm / MM_PER_TICK);
    
    // Xác định chiều quay động cơ: + xoay phải, - xoay trái
    state.turnDir = (angleDeg > 0) ? 1 : -1;

    // Khởi tạo lại toàn bộ bộ đếm xung trước khi chuyển động
    encA = 0; encB = 0; encC = 0; encD = 0;

    Serial.printf("[ESP32] TURN angle=%d dir=%d ticks=%ld\n",
                  angleDeg, state.turnDir, state.targetTicks);
}

// ─────────────────────────────────────────────────────────────────────────────
//  HÀM ĐIỀU PHỐI ĐỘNG CƠ TRONG MỖI CHU KỲ (10ms)
// ─────────────────────────────────────────────────────────────────────────────
void _controlMotors() {
    if (!state.moving && !state.turning) {
        return; // Đang đứng yên, không tác động xung PWM
    }

    // Áp đặt tốc độ chạy thẳng theo yêu cầu, tốc độ xoay hướng mặc định 180 để thắng ma sát bánh Mecanum xoay góc
    float targetPwm = state.moving ? (float)state.moveSpeed : 180.0f; 
    
    state.currentPwm = targetPwm;
    int pwm = (int)state.currentPwm;

    if (state.moving) {
        // Đi thẳng: Phát xung đồng thuận cho cả 4 bánh
        driveForward(pwm);
    }
    else if (state.turning) {
        // Xoay hướng: Bánh trái quay xuôi, bánh phải quay ngược hoặc ngược lại
        int leftPwm  =  state.turnDir * pwm;   // Động cơ AB bên trái
        int rightPwm = -state.turnDir * pwm;   // Động cơ CD bên phải
        driveTurn(leftPwm, rightPwm);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  KIỂM TRA VÀ XÁC NHẬN CHẠM ĐÍCH DỰA TRÊN ĐẾM XUNG ENCODER
// ─────────────────────────────────────────────────────────────────────────────
void _checkArrival() {
    if (!state.moving && !state.turning) return;

    // Lấy giá trị trung bình cộng số xung encoder của cả 4 bánh để triệt tiêu sai số trượt bánh
    long avg = (abs(encA) + abs(encB) + abs(encC) + abs(encD)) / 4;
    state.ticksMoved = avg;

    // Debug mỗi 500ms
    static unsigned long lastDbg = 0;
    if (millis() - lastDbg >= 500) {
        Serial.printf("[DBG] ticks=%ld/%ld | A:%ld B:%ld C:%ld D:%ld | pwm=%.0f\n",
                      avg, state.targetTicks, encA, encB, encC, encD, state.currentPwm);
        lastDbg = millis();
    }

    if (state.moving && avg >= state.targetTicks) {
        _stopAll();
        state.row = _nextRow;
        state.col = _nextCol;
        state.stepDone++;
        Serial.printf("[ESP32] ARRIVED (%d,%d)\n", state.row, state.col);
        
        char buf[64];
        snprintf(buf, sizeof(buf), "{\"ack\":\"DONE\",\"node\":[%d,%d]}", state.row, state.col);
        _sendRaw(buf);
    }
    else if (state.turning && avg >= state.targetTicks) {
        _stopAll();
        state.heading = state.targetHeading;
        Serial.printf("[ESP32] TURN DONE heading=%d\n", state.heading);
        
        char buf[64];
        snprintf(buf, sizeof(buf), "{\"ack\":\"TURN_DONE\",\"heading\":%d}", state.heading);
        _sendRaw(buf);
    }
}

// ─────────────────────────────────────────────────
//  DỪNG
// ─────────────────────────────────────────────────
void _stopAll() {
    state.moving     = false;
    state.turning    = false;
    state.dirName    = "IDLE";
    state.currentPwm = 0;
    stopAllMotors();
}

// ─────────────────────────────────────────────────
//  GỬI DỮ LIỆU LÊN Pi5
// ─────────────────────────────────────────────────
void _publishPosition() {
    float curR, curC;
    _getCurrentPosFloat(curR, curC);
    
    char buf[96];
    snprintf(buf, sizeof(buf),
             "{\"pos\":[%.3f,%.3f],\"heading\":%d,\"moving\":%s}",
             curR, curC, state.heading,
             state.moving ? "true" : "false");
    _sendRaw(buf);
}

void _sendRaw(const char* msg) {
    Pi5Serial.println(msg);
    Serial.print("[TX] "); Serial.println(msg);
}

