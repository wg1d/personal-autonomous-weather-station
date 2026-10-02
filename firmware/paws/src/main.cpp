/*
 * Project: Personal Autonomous Weather Station
 * File: src/main.cpp
 *
 * Description:
 * Firmware of the station (step A2): the state machine runs with the
 * DS3231 clock, which timestamps the rows and wakes the ESP32 up on the
 * measurement grid. The other modules are still skeleton adapters.
 *
 * Wiring:
 * - DS3231: 3.3V -> VCC, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL,
 *           Pin 36 -> SQW (10k pull-up resistor to 3.3V)
 * Dependencies: ESP32 Arduino core, RTClib, lib/core, lib/ports.
 */

#include <Arduino.h>

#include "StateMachine.h"
#include "adapters/Ds3231Clock.h"
#include "adapters/Esp32Power.h"
#include "adapters/NoMaintenance.h"
#include "adapters/NoNetwork.h"
#include "adapters/NullSensor.h"
#include "adapters/SerialLog.h"
#include "adapters/SerialStorage.h"

/// A short interval for the demo on the bench, instead of 15 minutes
const uint32_t kDemoIntervalS = 60;

Ds3231Clock rtcClock;
NullSensor sensor;
SerialStorage storage;
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
