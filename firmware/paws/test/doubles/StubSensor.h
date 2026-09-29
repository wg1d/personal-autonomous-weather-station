/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/StubSensor.h
 *
 * Description:
 * Stub sensor: always returns the same values, or nothing at all to
 * simulate a sensor that does not respond.
 *
 * Dependencies: lib/ports.
 */

#pragma once

#include "ISensor.h"

/**
 * @brief Stub sensor: fixed values, or none at all.
 */
class StubSensor : public ISensor {
public:
    bool responding = true;  ///< false simulates a sensor failure

    Measurement read() override {
        Measurement m;  // all NaN
        if (responding) {
            m.temperatureC = 18.4f;
            m.humidityPct = 62.0f;
            m.pressureHpa = 1013.2f;
        }
        return m;
    }
};
