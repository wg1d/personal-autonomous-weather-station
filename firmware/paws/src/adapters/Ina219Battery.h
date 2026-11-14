/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/Ina219Battery.h
 *
 * Description:
 * Battery monitor: the INA219 reads the voltage and the current of the
 * battery once per wake-up, then goes back to its power-down mode.
 *
 * Wiring (see the Power chapter of the outdoor station):
 * - INA219: VCC -> 3.3V, GND -> GND, SDA and SCL on the I2C bus of the
 *           board (see Board.h)
 * - VIN+ -> BATT of the charger, VIN- -> + of the battery: the current of
 *   the battery goes through the shunt, from the charger to the battery
 *   when it charges
 * Dependencies: ESP32 Arduino core, Adafruit INA219 Library.
 */

#pragma once

#include <Adafruit_INA219.h>
#include <Arduino.h>

#include "Board.h"
#include "Console.h"
#include "Record.h"

/// I2C address of the INA219 module (A0 and A1 left open)
const uint8_t kIna219Address = 0x40;

/**
 * @brief The battery monitor, read with the other sensors.
 *
 * If the INA219 does not answer, the values of the battery stay missing
 * (NaN), and the station keeps its schedule (N1). The bench station has
 * no INA219: its rows never have values for the battery.
 */
class Ina219Battery {
public:
    /**
     * @brief Reads the voltage and the current of the battery.
     *
     * @param[in,out] measurement Where the values are written; they stay
     *                NaN if the INA219 does not answer.
     */
    void read(Measurement& measurement) {
        if (!beginWithRetries()) {
            console.println("   INA219 not responding");
            return;
        }
        // A range of 16 V and 400 mA: the battery stays below 4.3 V, and
        // its current, between the panel and the awake station, below
        // 400 mA; the finest step of the chip is then about 0.1 mA
        ina_.setCalibration_16V_400mA();
        // The voltage on the side of the battery (VIN-), against the
        // ground of the station: the voltage of the battery
        measurement.batteryV = ina_.getBusVoltage_V();
        // Positive from VIN+ to VIN-: from the charger to the battery,
        // when it charges
        measurement.batteryMa = ina_.getCurrent_mA();
        // Power-down mode until the next wake-up: about 6 µA instead of
        // about 1 mA (INA219 datasheet)
        ina_.powerSave(true);
    }

private:
    // The INA219 left in power-down mode by the previous wake-up answers
    // on the bus; begin() wakes it up. A chip that does not answer at once
    // gets a few more tries, as for the other sensors (see Board.h)
    bool beginWithRetries() {
        for (int attempt = 0; attempt < kSensorTries; ++attempt) {
            if (ina_.begin()) {
                return true;
            }
            delay(kSensorRetryDelayMs);
        }
        return false;
    }

    Adafruit_INA219 ina_{kIna219Address};
};
