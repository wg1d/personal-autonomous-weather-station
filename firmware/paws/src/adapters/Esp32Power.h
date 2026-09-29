/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/Esp32Power.h
 *
 * Description:
 * ESP32 power adapter: reads the wake-up cause and enters deep sleep.
 * In step A1 only the safety timer is armed; the RTC alarm (EXT0) is
 * added in A2 and the button (EXT1) in A5.
 *
 * Wiring: none in A1.
 * Dependencies: ESP32 Arduino core (ESP-IDF sleep functions).
 */

#pragma once

#include <Arduino.h>
#include <esp_sleep.h>

#include "IPower.h"

/**
 * @brief ESP32 power management: wake-up cause and deep sleep.
 *
 * In step A1, only the safety timer of the plan is armed.
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
        Serial.printf("   RTC alarm: %s, button: %s, timer: %lu s\n",
                      plan.rtcAlarm ? "yes" : "no",
                      plan.button ? "not wired before A5" : "no",
                      static_cast<unsigned long>(plan.timerSeconds));
        // N3: awake time of this wake-up, measured by the firmware itself
        Serial.printf("   awake for %lu ms\n",
                      static_cast<unsigned long>(millis()));
        // Send the whole message before the UART is powered down
        Serial.flush();

        esp_sleep_enable_timer_wakeup(
            static_cast<uint64_t>(plan.timerSeconds) * 1000000ULL);
        esp_deep_sleep_start();
    }
};
