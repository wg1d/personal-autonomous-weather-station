/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/SystemClock.h
 *
 * Description:
 * Skeleton clock adapter (step A1), replaced by the DS3231 adapter in
 * A2. It uses the ESP32 system clock, which keeps counting during deep
 * sleep but restarts at 1970 after a power-on. It has no alarm: the
 * safety timer is then the only wake-up source.
 *
 * Wiring: none.
 * Dependencies: ESP32 Arduino core (POSIX time functions).
 */

#pragma once

#include <Arduino.h>
#include <sys/time.h>
#include <time.h>

#include "IClock.h"

/// Any time before this date (2026-01-01T00:00:00Z) means that the
/// clock restarted from 1970 and was never set
const uint32_t kClockValidAfter = 1767225600;

/// Time of the last setTime(), kept in RTC memory across deep sleep
RTC_DATA_ATTR static uint32_t systemClockLastSet = 0;

/**
 * @brief Skeleton clock: the ESP32 system clock, without alarm.
 */
class SystemClock : public IClock {
public:
    uint32_t now() override {
        return static_cast<uint32_t>(time(nullptr));
    }

    bool isValid() override { return now() >= kClockValidAfter; }

    void setTime(uint32_t unixTime) override {
        timeval tv = {static_cast<time_t>(unixTime), 0};
        settimeofday(&tv, nullptr);
        systemClockLastSet = unixTime;
    }

    uint32_t lastSetTime() override { return systemClockLastSet; }

    bool setAlarm(uint32_t /*unixTime*/) override {
        return false;  // no alarm hardware before step A2
    }
};
