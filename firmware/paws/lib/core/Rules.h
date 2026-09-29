/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/Rules.h
 *
 * Description:
 * The decisions of the state machine, as pure functions: same inputs,
 * same result, no hardware. They are tested one by one on the computer.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstdint>

#include "Config.h"

/**
 * @brief Start of the grid slot that contains a time.
 *
 * @param[in] t A Unix time, UTC.
 * @param[in] config Gives the measurement interval.
 * @return `t` rounded down to the measurement interval.
 */
uint32_t slotStart(uint32_t t, const Config& config);

/**
 * @brief Time of the next measurement (F1).
 *
 * @param[in] now The current Unix time, UTC.
 * @param[in] config Gives the measurement interval.
 * @return The next slot of the grid, strictly after `now`.
 */
uint32_t nextAlarm(uint32_t now, const Config& config);

/**
 * @brief Tells whether this wake-up must upload the rows (F3, F6).
 *
 * @param[in] measuredAt Time of the measurement (Unix time, UTC).
 * @param[in] clockValid Whether the clock is reliable.
 * @param[in] config Gives the measurement interval and upload period.
 * @return true when the measurement belongs to a full-hour slot, or when
 *         the clock is invalid (to reach NTP as soon as possible).
 */
bool isUploadNeeded(uint32_t measuredAt, bool clockValid,
                    const Config& config);

/**
 * @brief Tells whether the clock must be synchronized with NTP (F4).
 *
 * @param[in] now The current Unix time, UTC.
 * @param[in] clockValid Whether the clock is reliable.
 * @param[in] lastSync Time of the last NTP sync, or 0 if none is known.
 * @param[in] config Gives the sync period.
 * @return true when the clock is invalid, or when the last sync is at
 *         least one sync period old.
 */
bool isSyncNeeded(uint32_t now, bool clockValid, uint32_t lastSync,
                  const Config& config);

/**
 * @brief Duration of the safety timer (N2).
 *
 * @param[in] now The current Unix time, UTC.
 * @param[in] alarm The time of the programmed alarm.
 * @param[in] alarmSet Whether the alarm could be programmed.
 * @param[in] config Gives the safety margin and measurement interval.
 * @return The number of seconds until the safety margin after the alarm,
 *         or one measurement interval when no alarm could be programmed.
 */
uint32_t safetyTimerSeconds(uint32_t now, uint32_t alarm, bool alarmSet,
                            const Config& config);
