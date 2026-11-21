/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/I2cBus.h
 *
 * Description:
 * Frees the I2C bus when a chip holds one of its lines low. On the I2C
 * bus, the clock (SCL) and the data (SDA) lines rest high; a chip pulls a
 * line low to talk. A chip stopped in the middle of a byte, for example
 * when the ESP32 went to sleep or restarted while it answered, keeps SDA
 * low and waits for the rest of the clock pulses: the bus is then blocked
 * for every chip, and none of them answers. Up to 9 clock pulses let it
 * finish its byte and release SDA; a STOP condition then ends the
 * exchange. This is the recovery of the I2C specification (NXP UM10204,
 * section 3.1.16, "Bus clear").
 *
 * Wiring: the I2C pins of the board (SDA, SCL), see Board.h.
 * Dependencies: ESP32 Arduino core (Wire, digital pins), Console.h.
 */

#pragma once

#include <Arduino.h>
#include <Wire.h>

#include "Console.h"

/// Clock pulses sent to a chip stuck in the middle of a byte: its 8 bits
/// and the acknowledge bit
const int kI2cRecoveryPulses = 9;

/// Half a period of the clock of the recovery, in microseconds: 5 µs gives
/// 100 kHz, the standard speed of the I2C bus
const uint32_t kI2cHalfPeriodUs = 5;

/**
 * @brief Frees the I2C bus if a chip holds one of its lines low.
 *
 * Called at the start of each wake-up, before any chip is read, and again
 * when a chip does not answer. When both lines are high, the bus is free:
 * nothing is sent, and nothing is written in the log. Otherwise, the log
 * tells which line was held low, and whether the bus could be freed: a
 * bus that stays blocked, or chips that stay silent on a free bus, point
 * to the wiring or the power of the modules instead.
 *
 * The bus is stopped while its lines are read (Wire.end()), then started
 * again (Wire.begin()): the clock, already started at the boot, keeps
 * using it for its alarm.
 *
 * @return true if a line was held low.
 */
inline bool freeI2cBus() {
    Wire.end();
    pinMode(SDA, INPUT_PULLUP);
    pinMode(SCL, INPUT_PULLUP);
    delayMicroseconds(kI2cHalfPeriodUs);
    bool sdaLow = digitalRead(SDA) == LOW;
    bool sclLow = digitalRead(SCL) == LOW;
    if (!sdaLow && !sclLow) {
        Wire.begin();
        return false;  // the bus is free
    }
    console.printf("   I2C bus held low (SDA %s, SCL %s): freeing it\n",
                   sdaLow ? "low" : "high", sclLow ? "low" : "high");

    // Clock pulses, until the chip releases SDA. "Open drain": the pin
    // only pulls the line low, or lets the resistor pull it high, as the
    // chips do, so that a chip holding the line is never short-circuited
    pinMode(SCL, OUTPUT_OPEN_DRAIN);
    int pulses = 0;
    while (pulses < kI2cRecoveryPulses && digitalRead(SDA) == LOW) {
        digitalWrite(SCL, LOW);
        delayMicroseconds(kI2cHalfPeriodUs);
        digitalWrite(SCL, HIGH);
        delayMicroseconds(kI2cHalfPeriodUs);
        ++pulses;
    }

    // A STOP condition: SDA rises while SCL is high, which ends the
    // exchange for every chip on the bus
    pinMode(SDA, OUTPUT_OPEN_DRAIN);
    digitalWrite(SCL, LOW);
    digitalWrite(SDA, LOW);
    delayMicroseconds(kI2cHalfPeriodUs);
    digitalWrite(SCL, HIGH);
    delayMicroseconds(kI2cHalfPeriodUs);
    digitalWrite(SDA, HIGH);
    delayMicroseconds(kI2cHalfPeriodUs);

    pinMode(SDA, INPUT_PULLUP);
    pinMode(SCL, INPUT_PULLUP);
    bool freed = digitalRead(SDA) == HIGH && digitalRead(SCL) == HIGH;
    console.printf("   I2C bus %s after %d clock pulses\n",
                   freed ? "freed" : "still held low", pulses);
    Wire.begin();
    return true;
}
