/*
 * Project: Personal Autonomous Weather Station
 * File: src/main.cpp
 *
 * Description:
 * Firmware of the station (step A3): at each wake-up, the BME280 is read
 * and the row is appended to the CSV file of the SD card, timestamped by
 * the DS3231, whose alarm wakes the ESP32 up on the measurement grid.
 * The network and the maintenance mode are still skeleton adapters.
 *
 * Wiring:
 * - BME280: 3.3V -> VIN, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL
 * - DS3231: 3.3V -> VCC, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL,
 *           Pin 36 -> SQW (10k pull-up resistor to 3.3V)
 * - SD card: 5V -> VCC, GND -> GND, Pin 19 -> MISO, Pin 23 -> MOSI,
 *            Pin 18 -> SCLK, Pin 5 -> CS,
 *            Pin 13 -> OFF (10k pull-down resistor to GND)
 * Dependencies: ESP32 Arduino core, RTClib, Adafruit BME280 Library,
 * lib/core, lib/ports.
 */

#include <Arduino.h>

#include "StateMachine.h"
#include "adapters/Bme280Sensor.h"
#include "adapters/Ds3231Clock.h"
#include "adapters/Esp32Power.h"
#include "adapters/NoMaintenance.h"
#include "adapters/NoNetwork.h"
#include "adapters/SdStorage.h"
#include "adapters/SerialLog.h"

/// A short interval for the demo on the bench, instead of 15 minutes
const uint32_t kDemoIntervalS = 60;

Ds3231Clock rtcClock;
Bme280Sensor sensor;
SdStorage storage;
NoNetwork network;
Esp32Power power;
NoMaintenance maintenance;
SerialLog serialLog;

/// Runs one wake-up of the state machine, which ends in deep sleep
void setup() {
    Serial.begin(115200);
    Serial.println();

    // Without an answer, the clock reports an invalid time and the safety
    // timer takes over (N2): the station keeps running
    rtcClock.begin();

    Config config;
    config.measurementIntervalS = kDemoIntervalS;

    StateMachine machine(config,
                         {rtcClock, sensor, storage, network, power,
                          maintenance, serialLog});

    // Runs one wake-up and ends in deep sleep: it never returns
    machine.run();
}

void loop() {
    // Never reached: each wake-up is a fresh boot that runs setup()
}
