/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/Bme280Sensor.h
 *
 * Description:
 * Sensor adapter for the BME280: temperature, humidity and pressure,
 * read once per wake-up in forced mode.
 *
 * Wiring:
 * - BME280: 3.3V -> VIN, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL
 *           (same I2C bus as the DS3231)
 * Dependencies: ESP32 Arduino core, Adafruit BME280 Library.
 */

#pragma once

#include <Adafruit_BME280.h>
#include <Arduino.h>

#include "ISensor.h"

/// I2C address of the BME280 module (0x76 when SDO is tied to GND)
const uint8_t kBme280Address = 0x76;

/**
 * @brief Sensor adapter for the BME280.
 *
 * If the sensor does not answer, all the values stay missing (NaN), and
 * the station keeps its schedule (N1).
 */
class Bme280Sensor : public ISensor {
public:
    Measurement read() override {
        Measurement measurement;  // all values missing until read

        if (!bme_.begin(kBme280Address)) {
            Serial.println("   BME280 not responding");
            return measurement;
        }
        // Forced mode: one measurement on demand, then the sensor goes
        // back to sleep. The default, normal mode, measures non-stop and
        // would waste energy between two wake-ups.
        // These are the "weather monitoring" settings recommended by Bosch
        // (BME280 datasheet, section 3.5), as in the advancedsettings
        // example of the Adafruit library.
        bme_.setSampling(Adafruit_BME280::MODE_FORCED,
                         Adafruit_BME280::SAMPLING_X1,  // temperature
                         Adafruit_BME280::SAMPLING_X1,  // pressure
                         Adafruit_BME280::SAMPLING_X1,  // humidity
                         Adafruit_BME280::FILTER_OFF);
        if (!bme_.takeForcedMeasurement()) {
            Serial.println("   BME280 measurement timed out");
            return measurement;
        }

        measurement.temperatureC = bme_.readTemperature();
        measurement.humidityPct = bme_.readHumidity();
        // The library returns pascals; the CSV file uses hectopascals
        measurement.pressureHpa = bme_.readPressure() / 100.0f;
        return measurement;
    }

private:
    Adafruit_BME280 bme_;
};
