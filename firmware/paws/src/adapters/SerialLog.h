/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/SerialLog.h
 *
 * Description:
 * Log adapter: prints each state entered on the serial port, as
 * "-> BOOT", to follow a wake-up in the serial monitor.
 *
 * Wiring: none (USB serial only).
 * Dependencies: ESP32 Arduino core.
 */

#pragma once

#include <Arduino.h>

#include "ILog.h"

/**
 * @brief Log adapter: prints each state entered on the serial port.
 */
class SerialLog : public ILog {
public:
    void stateEntered(const char* name) override {
        Serial.printf("-> %s\n", name);
    }
};
