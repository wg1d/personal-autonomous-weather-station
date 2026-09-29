/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/NoMaintenance.h
 *
 * Description:
 * Skeleton maintenance adapter (step A1), replaced by the access point
 * and web page in A5. It returns at once.
 *
 * Wiring: none.
 * Dependencies: ESP32 Arduino core.
 */

#pragma once

#include <Arduino.h>

#include "IMaintenance.h"

/**
 * @brief Skeleton maintenance mode: returns at once.
 */
class NoMaintenance : public IMaintenance {
public:
    void run(uint32_t /*durationS*/) override {
        Serial.println("   no maintenance mode before step A5");
    }
};
