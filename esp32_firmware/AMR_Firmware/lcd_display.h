// ═══════════════════════════════════════════════════
//  lcd_display.h — LCD 1602 I2C hiển thị vị trí AMR
//  Dùng LiquidCrystal_I2C library
//
//  Hàng 1: "X:03 Y:05 B:04 "   (Vị trí + Số bước)
//  Hàng 2: "Dir: TIEN  90° "   (Hướng đi + Góc)
// ═══════════════════════════════════════════════════
#pragma once
#include <Arduino.h>
#include <LiquidCrystal_I2C.h>
#include "config.h"

class LCDDisplay {
public:
    LCDDisplay() : _lcd(LCD_ADDR, 16, 2) {}

    void begin() {
        _lcd.init();
        _lcd.backlight();
        _lcd.setCursor(0, 0);
        _lcd.print("AMR Digital Twin");
        _lcd.setCursor(0, 1);
        _lcd.print("Khoi dong...");
        delay(1500);
        _lcd.clear();
    }

    // Cập nhật vị trí, hướng và số bước lên LCD
    // Hàng 1: "X:03 Y:05 B:04 "
    // Hàng 2: "Dir: TIEN  90° "
    void update(int row, int col,
                int heading,
                const char* dirName,
                int stepDone) {
        unsigned long now = millis();
        if (now - _lastUpdate < LCD_UPDATE_MS) return;
        _lastUpdate = now;

        // Hàng 1: Vị trí (X,Y) + Số bước
        _lcd.setCursor(0, 0);
        char buf[17];
        snprintf(buf, sizeof(buf), "X:%02d Y:%02d B:%02d  ", col, row, stepDone);
        _lcd.print(buf);

        // Hàng 2: Hướng đi + Góc
        _lcd.setCursor(0, 1);
        char buf2[17];
        snprintf(buf2, sizeof(buf2), "Dir:%-5s %3d%c  ", dirName, heading, 0xDF);
        _lcd.print(buf2);
    }

    void showMessage(const char* line1, const char* line2 = "") {
        _lcd.clear();
        _lcd.setCursor(0, 0); _lcd.print(line1);
        _lcd.setCursor(0, 1); _lcd.print(line2);
    }

private:
    LiquidCrystal_I2C _lcd;
    unsigned long _lastUpdate = 0;
};
