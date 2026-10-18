/*
 * Project: Personal Autonomous Weather Station
 * Tool: bench_check.ino
 *
 * Description:
 * Checks the wiring of the outdoor station on the bench, before its
 * firmware runs on the XIAO ESP32-S3 (step O2). Every two seconds, it
 * prints on the serial monitor:
 * - the modules found on the I2C bus, with their name when known;
 * - the state of the maintenance button (D1) and of the alarm output of
 *   the clock (SQW, on D0).
 * A module plugged in or a button pressed shows up at the next print.
 *
 * Wiring: Grove Shield for XIAO; I2C on the I2C connectors (SDA = D4,
 * SCL = D5); the D0/D1 connector: yellow (D0) to SQW of the clock, white
 * (D1) and black (GND) to the button.
 *
 * Dependencies: Arduino core for the ESP32 (Wire).
 */

#include <Arduino.h>
#include <Wire.h>

// The button closes D1 to the ground while it is pressed. The internal
// pull-up resistor keeps D1 high the rest of the time.
const uint8_t kButtonPin = D1;

// The alarm output of the clock (SQW) goes low when the alarm fires. The
// clock module has its own pull-up resistor on this line.
const uint8_t kAlarmPin = D0;

const unsigned long kPeriodMs = 2000;

// The modules the station may have, by their I2C address
const char* moduleName(uint8_t address) {
    switch (address) {
        case 0x68: return "DS3231 clock";
        case 0x57: return "AT24C32 memory of the clock module (unused)";
        case 0x76:
        case 0x77: return "BME280 or BMP280 (pressure)";
        case 0x44:
        case 0x45: return "SHT31 (temperature, humidity)";
        case 0x40: return "INA219 battery monitor";
        default: return "unknown module";
    }
}

// Asks each address in turn whether a module answers
void scanBus() {
    int found = 0;
    Serial.println("I2C modules:");
    for (uint8_t address = 0x08; address < 0x78; address++) {
        Wire.beginTransmission(address);
        // 0 means that a module acknowledged its address
        if (Wire.endTransmission() == 0) {
            Serial.printf("  0x%02X  %s\n", address, moduleName(address));
            found++;
        }
    }
    if (found == 0) {
        Serial.println("  none: check the Grove cables and the switch");
    }
}

void setup() {
    Serial.begin(115200);
    // The USB serial port of the XIAO needs a moment after a reset
    delay(2000);
    Serial.println("\nPAWS bench check (XIAO ESP32-S3)");

    Wire.begin();  // the pins of the board: SDA = D4, SCL = D5
    pinMode(kButtonPin, INPUT_PULLUP);
    pinMode(kAlarmPin, INPUT_PULLUP);
}

void loop() {
    scanBus();
    Serial.printf("Button (D1): %s\n",
                  digitalRead(kButtonPin) == LOW ? "PRESSED" : "released");
    Serial.printf("Clock alarm (D0): %s\n\n",
                  digitalRead(kAlarmPin) == LOW ? "fired (low)"
                                                : "idle (high)");
    delay(kPeriodMs);
}
