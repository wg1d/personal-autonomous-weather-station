/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/SerialStorage.h
 *
 * Description:
 * Skeleton storage adapter (step A1), replaced by the SD card adapter in
 * A3. It prints each row on the serial port instead of storing it.
 *
 * Wiring: none (USB serial only).
 * Dependencies: ESP32 Arduino core.
 */

#pragma once

#include <Arduino.h>
#include <time.h>

#include "IStorage.h"

/**
 * @brief Skeleton storage: prints each row on the serial port.
 */
class SerialStorage : public IStorage {
public:
    bool append(const Record& record) override {
        time_t t = record.timestamp;
        tm utc;
        gmtime_r(&t, &utc);
        char iso[21];  // 2026-10-01T14:15:00Z
        strftime(iso, sizeof(iso), "%Y-%m-%dT%H:%M:%SZ", &utc);

        // Printed with %f, a missing value (NaN) appears as "nan"
        Serial.printf("   row: %s time_valid=%d T=%.2f H=%.2f P=%.2f\n",
                      iso, record.timeValid ? 1 : 0,
                      record.values.temperatureC,
                      record.values.humidityPct,
                      record.values.pressureHpa);
        return true;
    }
};
