/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/StationSensors.h
 *
 * Description:
 * The sensors of the station, read at each wake-up as one measurement:
 * the BME280 for the air, then the INA219 for the battery.
 *
 * Wiring: see Bme280Sensor.h and Ina219Battery.h.
 * Dependencies: Bme280Sensor.h, Ina219Battery.h.
 */

#pragma once

#include "Bme280Sensor.h"
#include "ISensor.h"
#include "Ina219Battery.h"

/**
 * @brief All the sensors of the station, behind the single sensor port of
 * the core.
 *
 * The core only knows one sensor, which gives one Measurement: adding the
 * battery monitor adds two values to the measurement, without changing
 * the state machine (N5). Each part fails on its own: without the BME280,
 * the battery is still read, and the other way round.
 */
class StationSensors : public ISensor {
public:
    Measurement read() override {
        Measurement measurement = air_.read();
        battery_.read(measurement);
        return measurement;
    }

private:
    Bme280Sensor air_;
    Ina219Battery battery_;
};
