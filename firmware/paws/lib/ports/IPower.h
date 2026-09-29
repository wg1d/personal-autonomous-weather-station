/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/IPower.h
 *
 * Description:
 * What the core needs from the power management: why the chip woke up,
 * and a way to sleep with the chosen wake-up sources.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstdint>

/**
 * @brief Why the station woke up.
 */
enum class WakeCause {
    PowerOn,   ///< First boot, reset, or anything unexpected
    RtcAlarm,  ///< DS3231 alarm (EXT0)
    Button,    ///< Maintenance button (EXT1)
    Timer,     ///< ESP32 safety timer
};

/**
 * @brief The wake-up sources to arm before sleeping, chosen by the core.
 */
struct SleepPlan {
    bool rtcAlarm = false;      ///< An RTC alarm was programmed
    bool button = false;        ///< The button can wake the station up
    uint32_t timerSeconds = 0;  ///< Safety timer, always armed (N2)
};

/**
 * @brief The power management of the station.
 *
 * Implemented by the ESP32 adapter on the board, and by a fake in the
 * tests.
 */
class IPower {
public:
    virtual ~IPower() = default;

    /**
     * @brief Tells why the station woke up.
     *
     * Called once per wake-up, at the start.
     *
     * @return The wake-up cause.
     */
    virtual WakeCause wakeCause() = 0;

    /**
     * @brief Arms the wake-up sources of the plan, then sleeps.
     *
     * On the board, enters deep sleep and never returns: the next wake-up
     * is a fresh boot. In the tests, records the plan and returns.
     *
     * @param[in] plan The wake-up sources to arm.
     */
    virtual void sleep(const SleepPlan& plan) = 0;
};
