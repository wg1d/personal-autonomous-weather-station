/*
 * Project: Personal Autonomous Weather Station
 * File: src/main.cpp
 *
 * Description:
 * Firmware of the station (step A5): at each wake-up, the BME280 is read
 * and the row is appended to the CSV file of the SD card, timestamped by
 * the DS3231, whose alarm wakes the ESP32 up on the measurement grid.
 * Once per hour, the station connects to the home Wi-Fi and sends the new
 * rows to the server; once per day, it sets the DS3231 with NTP. A press
 * on the button starts the maintenance mode: an access point and a web
 * page to download or delete the data, for 3 minutes.
 *
 * Wiring:
 * - BME280: 3.3V -> VIN, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL
 * - DS3231: 3.3V -> VCC, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL,
 *           Pin 36 -> SQW (10k pull-up resistor to 3.3V)
 * - SD card: 5V -> VCC, GND -> GND, Pin 19 -> MISO, Pin 23 -> MOSI,
 *            Pin 18 -> SCLK, Pin 5 -> CS,
 *            Pin 13 -> OFF (10k pull-down resistor to GND)
 * - Button: 3.3V -> button -> Pin 39 (10k pull-down resistor to GND)
 * Dependencies: ESP32 Arduino core, RTClib, Adafruit BME280 Library,
 * lib/core, lib/ports, include/secrets.h (Wi-Fi, server and access
 * point settings).
 */

#include <Arduino.h>
#include <esp_task_wdt.h>

#include "StateMachine.h"
#include "adapters/AccessPointMaintenance.h"
#include "adapters/Bme280Sensor.h"
#include "adapters/Console.h"
#include "adapters/Ds3231Clock.h"
#include "adapters/Esp32Power.h"
#include "adapters/SdStorage.h"
#include "adapters/SerialLog.h"
#include "adapters/WifiNetwork.h"
#include "secrets.h"

// Set to 1 by the esp32-bench environment of platformio.ini
#ifndef PAWS_BENCH_DEMO
#define PAWS_BENCH_DEMO 0
#endif

/// true when built with the esp32-bench environment: one measurement per
/// minute and one upload every 5 minutes, to see the whole cycle quickly
/// on the bench. false with the esp32 environment, for the station: the
/// periods of the design, 15 minutes and one hour.
const bool kBenchDemo = PAWS_BENCH_DEMO;

/// Longest normal wake-up, with margin: a maintenance session (3 minutes)
/// followed by a large upload. Beyond it, the firmware is considered stuck,
/// and the watchdog restarts the chip.
const uint32_t kWatchdogS = 10 * 60;

/// The console of the adapters: serial port, and log of the wake-up
Console console;

Ds3231Clock rtcClock;
Bme280Sensor sensor;
SdCard card;
SdStorage storage(card);
WifiNetwork network(kWifiSsid, kWifiPassword, kServerUrl);
Esp32Power power;
AccessPointMaintenance maintenance(card, kApSsid, kApPassword,
                                   PAWS_VERSION);
SerialLog serialLog;

/// Runs one wake-up of the state machine, which ends in deep sleep
void setup() {
    Serial.begin(115200);
    console.printf("\nPAWS firmware %s%s\n", PAWS_VERSION,
                   kBenchDemo ? " (bench periods)" : "");

    // If this wake-up ever freezes (a library waiting forever, for
    // example), the watchdog restarts the chip: the next boot measures and
    // goes back to the normal cycle instead of staying awake (N2, N3).
    // The Arduino core already starts this watchdog; this sets its delay
    // and makes it watch setup().
    esp_task_wdt_init(kWatchdogS, true);
    esp_task_wdt_add(nullptr);

    // Without an answer, the clock reports an invalid time and the safety
    // timer takes over (N2): the station keeps running
    rtcClock.begin();

    Config config;
    if (kBenchDemo) {
        config.measurementIntervalS = 60;
        config.uploadPeriodS = 5 * 60;
    }

    StateMachine machine(config,
                         {rtcClock, sensor, storage, network, power,
                          maintenance, serialLog});

    // Runs one wake-up and ends in deep sleep: it never returns
    machine.run();
}

void loop() {
    // Never reached: each wake-up is a fresh boot that runs setup()
}
