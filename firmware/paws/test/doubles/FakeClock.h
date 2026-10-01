/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/FakeClock.h
 *
 * Description:
 * Fake clock: the test sets and advances the time, chooses whether the
 * clock is valid and whether alarms work, and reads the last alarm.
 *
 * Dependencies: lib/ports.
 */

#pragma once

#include <cstdint>

#include "IClock.h"

/**
 * @brief Fake clock, whose time and behavior the test controls.
 */
class FakeClock : public IClock {
public:
    uint32_t time = 0;       ///< Time returned by now()
    bool valid = true;       ///< Value returned by isValid()
    bool alarmWorks = true;  ///< false simulates an RTC failure (N2)

    uint32_t lastSet = 0;    ///< Value returned by lastSetTime()
    uint32_t lastAlarm = 0;  ///< Last alarm programmed, 0 if none
    int setTimeCount = 0;    ///< Number of calls to setTime()

    uint32_t now() override { return time; }
    bool isValid() override { return valid; }

    void setTime(uint32_t unixTime) override {
        time = unixTime;
        valid = true;
        lastSet = unixTime;
        ++setTimeCount;
    }

    uint32_t lastSetTime() override { return lastSet; }

    bool setAlarm(uint32_t unixTime) override {
        if (!alarmWorks) {
            return false;
        }
        lastAlarm = unixTime;
        return true;
    }

    /**
     * @brief Moves the time forward, as if time had passed.
     *
     * @param[in] seconds The number of seconds to add.
     */
    void advance(uint32_t seconds) { time += seconds; }
};
