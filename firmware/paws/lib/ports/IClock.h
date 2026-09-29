/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/IClock.h
 *
 * Description:
 * What the core needs from a clock, and nothing more.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstdint>

/**
 * @brief The clock that gives the time and wakes the station up.
 *
 * All times are Unix timestamps (seconds since 1970-01-01T00:00:00Z),
 * in UTC. Implemented by the DS3231 adapter on the board, and by a fake
 * clock in the tests.
 */
class IClock {
public:
    virtual ~IClock() = default;

    /**
     * @brief Returns the current time.
     *
     * Always returns the time held by the clock, even when it is not
     * reliable: isValid() tells whether it can be trusted.
     *
     * @return The current Unix time, UTC.
     */
    virtual uint32_t now() = 0;

    /**
     * @brief Tells whether the time can be trusted.
     *
     * @return false after a power loss of the clock, until setTime() is
     *         called; true otherwise.
     */
    virtual bool isValid() = 0;

    /**
     * @brief Sets the time, after a successful NTP sync.
     *
     * After this call, isValid() returns true.
     *
     * @param[in] unixTime The new Unix time, UTC.
     */
    virtual void setTime(uint32_t unixTime) = 0;

    /**
     * @brief Programs the alarm that wakes the station up.
     *
     * Replaces any previous alarm. The core always passes a time strictly
     * in the future, on the measurement grid.
     *
     * @param[in] unixTime When the alarm must fire (Unix time, UTC).
     * @return true if the alarm is programmed; false if it could not be
     *         (no alarm hardware, or RTC not responding). The safety timer
     *         is then the only way to wake up again (N2).
     */
    virtual bool setAlarm(uint32_t unixTime) = 0;
};
