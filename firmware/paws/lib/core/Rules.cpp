/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/Rules.cpp
 *
 * Description:
 * Implementation of the pure decision rules (see Rules.h).
 *
 * Dependencies: none (standard C++ only).
 */

#include "Rules.h"

uint32_t slotStart(uint32_t t, const Config& config) {
    return t - t % config.measurementIntervalS;
}

uint32_t nextAlarm(uint32_t now, const Config& config) {
    return slotStart(now, config) + config.measurementIntervalS;
}

bool isUploadNeeded(uint32_t measuredAt, bool clockValid,
                    const Config& config) {
    if (!clockValid) {
        // Try to reach NTP at every wake-up until the clock is valid
        return true;
    }
    // The wake-up happens a few seconds after the alarm (or 60 s after it
    // for the safety timer), so the measurement time itself is never
    // exactly on the hour: we test the slot it belongs to.
    return slotStart(measuredAt, config) % config.uploadPeriodS == 0;
}

bool isSyncNeeded(uint32_t now, bool clockValid, uint32_t lastSync,
                  const Config& config) {
    if (!clockValid) {
        return true;
    }
    // A clock that went backwards (now < lastSync) is suspicious too:
    // the unsigned subtraction then gives a huge age, hence a sync.
    return now - lastSync >= config.syncPeriodS;
}

uint32_t safetyTimerSeconds(uint32_t now, uint32_t alarm, bool alarmSet,
                            const Config& config) {
    if (!alarmSet) {
        return config.measurementIntervalS;
    }
    return alarm - now + config.safetyMarginS;
}
