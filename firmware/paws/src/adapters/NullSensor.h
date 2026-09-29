/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/NullSensor.h
 *
 * Description:
 * Skeleton sensor adapter (step A1), replaced by the BME280 adapter in
 * A3. It returns missing values only.
 *
 * Wiring: none.
 * Dependencies: none.
 */

#pragma once

#include "ISensor.h"

/**
 * @brief Skeleton sensor: all values are always missing.
 */
class NullSensor : public ISensor {
public:
    Measurement read() override {
        return Measurement{};  // all values missing (NaN)
    }
};
