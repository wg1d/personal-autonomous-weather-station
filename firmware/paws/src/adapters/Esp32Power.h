/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/Esp32Power.h
 *
 * Description:
 * ESP32 power adapter: reads the wake-up cause and enters deep sleep,
 * woken by the DS3231 alarm (EXT0), the maintenance button (EXT1) and
 * the safety timer.
 *
 * Wiring: the pins of the board, in Board.h.
 * - DS3231 SQW -> kRtcAlarmPin, pulled low when the alarm fires
 * - Button -> kButtonPin: active high on the uPesy (3.3V -> button, 10k
 *   pull-down resistor), active low on the XIAO (button -> GND, internal
 *   pull-up resistor)
 * Dependencies: ESP32 Arduino core (ESP-IDF sleep and RTC GPIO functions),
 * Board.h.
 */

#pragma once

#include <Arduino.h>
#include <driver/rtc_io.h>
#include <esp_sleep.h>

#include "Board.h"
#include "Console.h"
#include "IPower.h"

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
        // Send the whole message before the UART is powered down. Not on
        // the native USB port of the XIAO: its flush() would wait forever
        // when no computer reads the port, outdoors for example, and the
        // station would never sleep (see Board.h)
        if (!kSerialIsNativeUsb) {
            Serial.flush();
        }

        // Arm the alarm wake-up only if the core could program the alarm:
        // a DS3231 that does not answer may hold SQW low, which would wake
        // the station up again as soon as it sleeps
        if (plan.rtcAlarm) {
            // The DS3231 pulls SQW low (level 0) when the alarm fires
            esp_sleep_enable_ext0_wakeup(kRtcAlarmPin, 0);
        }

        if (plan.button) {
            armButton();
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

private:
    // EXT1 can watch several pins: a bit mask selects the button pin, and
    // the station wakes up when it changes to its pressed level
    // (kButtonWakeMode, in Board.h)
    void armButton() {
        if (kButtonActiveLow) {
            // The internal pull-up resistor keeps the pin high while the
            // button is released. In deep sleep, it only works if the RTC
            // part of the chip, which stays awake, keeps it on: its power
            // is kept on, and the resistor set through it
            esp_sleep_pd_config(ESP_PD_DOMAIN_RTC_PERIPH, ESP_PD_OPTION_ON);
            rtc_gpio_pullup_en(kButtonPin);
            rtc_gpio_pulldown_dis(kButtonPin);
        }
        // Otherwise, the pull-down resistor of the breadboard keeps the pin
        // low while the button is released
        esp_sleep_enable_ext1_wakeup(1ULL << kButtonPin, kButtonWakeMode);
    }
};
