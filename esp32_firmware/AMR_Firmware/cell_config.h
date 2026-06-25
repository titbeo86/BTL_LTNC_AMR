// ═══════════════════════════════════════════════════
//  cell_config.h — Quản lý kích thước ô động
//  Cho phép thay đổi cell size qua Serial từ Pi5
//  Lệnh: {"cmd":"CELL","mm":200}
// ═══════════════════════════════════════════════════
#pragma once
#include <Arduino.h>
#include "config.h"

class CellConfig {
public:
    // Kích thước ô hiện tại (mm)
    int    cellMM     = CELL_SIZE_MM_DEFAULT;

    // Ticks tương ứng (tính từ cellMM)
    long   ticksPerCell = 0;

    // Tốc độ PWM gợi ý theo ô
    int    speedPWM   = MOVE_SPEED_DEFAULT;

    CellConfig() { _recalc(); }

    // ── Đặt kích thước ô mới ────────────────────
    bool setCellMM(int mm) {
        // Chỉ cho phép các giá trị hợp lệ
        if (mm < 100 || mm > 500) {
            Serial.printf("[CELL] Giá trị không hợp lệ: %d mm (100-500)\n", mm);
            return false;
        }
        cellMM = mm;
        _recalc();
        Serial.printf("[CELL] Kích thước ô: %d mm → %ld ticks, speed=%d\n",
                      cellMM, ticksPerCell, speedPWM);
        return true;
    }

    // ── Các preset phổ biến ─────────────────────
    void preset150() { setCellMM(150); }
    void preset200() { setCellMM(200); }
    void preset250() { setCellMM(250); }
    void preset300() { setCellMM(300); }

    // ── In thông số hiện tại ────────────────────
    void printInfo() {
        Serial.println("─── Cell Config ───");
        Serial.printf("  Ô: %d mm\n",       cellMM);
        Serial.printf("  Ticks: %ld\n",     ticksPerCell);
        Serial.printf("  Speed PWM: %d\n",  speedPWM);
        Serial.printf("  mm/tick: %.4f\n",  MM_PER_TICK);
        Serial.println("──────────────────");
    }

private:
    void _recalc() {
        // Tính số tick = cell_mm / mm_per_tick
        ticksPerCell = (long)((float)cellMM / MM_PER_TICK);

        // Tốc độ gợi ý: ô nhỏ chạy chậm hơn để chính xác
        if      (cellMM <= 150) speedPWM = 150;
        else if (cellMM <= 200) speedPWM = 180;
        else if (cellMM <= 250) speedPWM = 190;
        else                    speedPWM = 200;
    }
};

// Instance toàn cục
CellConfig gCell;
