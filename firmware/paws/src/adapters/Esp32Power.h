/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/Esp32Power.h
 *
 * Description:
 * ESP32 power adapter: reads the wake-up cause and enters deep sleep,
 * woken by the DS3231 alarm (EXT0), the maintenance button (EXT1) and
 * the safety timer.
 *
 * Wiring:
 * - DS3231 SQW -> Pin 36 (10k pull-up resistor to 3.3V)
 * - Button: 3.3V -> button -> Pin 39 (10k pull-down resistor to GND)
 * Dependencies: ESP32 Arduino core (ESP-IDF sleep functions).
 */

#pragma once

#include <Arduino.h>
#include <esp_sleep.h>

#include "Console.h"
#include "IPower.h"

/// DS3231 SQW output: pulled low when the alarm fires
const gpio_num_t kRtcAlarmPin = GPIO_NUM_36;

/// Maintenance button: pulled high while it is pressed
const gpio_num_t kButtonPin = GPIO_NUM_39;

/**
 * @brief ESP32 power management: wake-up cause and deep sleep.
 *
 * Arms the wake-up sources of the plan: the RTC alarm, the button and
 * the safety timer.
 */
class Esp32Power : public IPower {
public:
    WakeCause wakeCause() override {
        switch (esp_sleep_get_wakeup_cause()) {
            case ESP_SLEEP_WAKEUP_EXT0:  return WakeCause::RtcAlarm;
            case ESP_SLEEP_WAKEUP_EXT1:  return WakeCause::Button;
            case ESP_SLEEP_WAKEUP_TIMER: return WakeCause::Timer;
            default:                     return WakeCause::PowerOn;
        }
    }

    void sleep(const SleepPlan& plan) override {
        console.printf("   RTC alarm: %s, button: %s, timer: %lu s\n",
                      plan.rtcAlarm ? "yes" : "no",
                      plan.button ? "yes" : "no",
                      static_cast<unsigned long>(plan.timerSeconds));
        // Send the whole message before the UART is powered down
        Serial.flush();

        // Arm the alarm wake-up only if the core could program the alarm:
        // a DS3231 that does not answer may hold SQW low, which would wake
        // the station up again as soon as it sleeps
        if (plan.rtcAlarm) {
            // The DS3231 pulls SQW low (level 0) when the alarm fires
            esp_sleep_enable_ext0_wakeup(kRtcAlarmPin, 0);
        }

        if (plan.button) {
            // EXT1 can watch several pins: a bit mask selects pin 39, and
            // the station wakes up when it goes high (button pressed)
            esp_sleep_enable_ext1_wakeup(1ULL << kButtonPin,
                                         ESP_EXT1_WAKEUP_ANY_HIGH);
        }

        // Safety timer (N2), always armed: if the alarm never comes, the
        // station still wakes up. Its duration is computed by the core
        // (safetyTimerSeconds(), in SCHEDULE); the ESP32 counts in
        // microseconds
        esp_sleep_enable_timer_wakeup(
            static_cast<uint64_t>(plan.timerSeconds) * 1000000ULL);

        // The chip stops here: the next wake-up restarts from setup()
        esp_deep_sleep_start();
    }
};
