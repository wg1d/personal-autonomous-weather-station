/*
 * Project: Personal Autonomous Weather Station
 * File: src/main.cpp
 *
 * Description:
 * Walking skeleton (step A1): the complete state machine runs on the
 * board, with skeleton adapters that stand in for the hardware. Each
 * wake-up prints the visited states and the row, then sleeps until the
 * safety timer wakes the chip up again.
 *
 * Wiring: none (ESP32 board and USB cable only).
 * Dependencies: ESP32 Arduino core, lib/core, lib/ports.
 */

#include <Arduino.h>

#include "StateMachine.h"
#include "adapters/Esp32Power.h"
#include "adapters/NoMaintenance.h"
#include "adapters/NoNetwork.h"
#include "adapters/NullSensor.h"
#include "adapters/SerialLog.h"
#include "adapters/SerialStorage.h"
#include "adapters/SystemClock.h"

/// A short interval for the demo on the bench, instead of 15 minutes
const uint32_t kDemoIntervalS = 20;

SystemClock rtcClock;
NullSensor sensor;
SerialStorage storage;
NoNetwork network;
Esp32Power power;
NoMaintenance maintenance;
SerialLog serialLog;

/// Runs one wake-up of the state machine, which ends in deep sleep
void setup() {
    Serial.begin(115200);

    Config config;
    config.measurementIntervalS = kDemoIntervalS;

    StateMachine machine(config,
                         {rtcClock, sensor, storage, network, power,
                          maintenance, serialLog});

    Serial.println();
    // Runs one wake-up and ends in deep sleep: it never returns
    machine.run();
}

void loop() {
    // Never reached: each wake-up is a fresh boot that runs setup()
}
