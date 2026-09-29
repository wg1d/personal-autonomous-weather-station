/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/Record.h
 *
 * Description:
 * The data exchanged between the core and the adapters: one measurement
 * of all sensors, and the row stored for each wake-up.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cmath>
#include <cstdint>

/**
 * @brief One reading of all the sensors.
 *
 * A value that could not be measured is NaN, never a fake number such
 * as 0 or -999. The storage writes it as an empty CSV field. Adding a
 * sensor adds a field here (N5).
 */
struct Measurement {
    float temperatureC = NAN;  ///< Air temperature, in °C
    float humidityPct = NAN;   ///< Relative humidity, in %
    float pressureHpa = NAN;   ///< Atmospheric pressure, in hPa
};

/**
 * @brief The row created at each wake-up, and appended to the storage.
 */
struct Record {
    uint32_t timestamp = 0;  ///< Time of the measurement (Unix time, UTC)
    bool timeValid = false;  ///< false if the clock was not reliable (F6)
    Measurement values;      ///< The values read from the sensors
};
