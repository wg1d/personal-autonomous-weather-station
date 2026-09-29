/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/ISensor.h
 *
 * Description:
 * What the core needs from the sensors: one reading of all values.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include "Record.h"

/**
 * @brief The sensors of the station, read all at once.
 *
 * Implemented by the BME280 adapter on the board, and by a stub sensor
 * in the tests.
 */
class ISensor {
public:
    virtual ~ISensor() = default;

    /**
     * @brief Reads all the sensors once.
     *
     * Called once per wake-up. A sensor failure must never stop the
     * schedule (N1): a value that could not be read is left as NaN.
     *
     * @return The values read; missing values are NaN.
     */
    virtual Measurement read() = 0;
};
