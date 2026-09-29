/*
 * Project: Personal Autonomous Weather Station
 * File: test/test_scenarios/Station.h
 *
 * Description:
 * Test fixture: a whole station built from test doubles. By default it
 * is 14:00:03 on 2026-10-01 (just after an alarm), with a valid clock, a
 * working sensor, storage and Wi-Fi. Each test changes what it needs,
 * then calls wake() to run the state machine once.
 *
 * Dependencies: lib/core, test/doubles.
 */

#pragma once

#include <cstdint>
#include <initializer_list>

#include "EventLog.h"
#include "FakeClock.h"
#include "FakeMaintenance.h"
#include "FakePower.h"
#include "FakeStorage.h"
#include "MockNetwork.h"
#include "StateMachine.h"
#include "StubSensor.h"

/// 2026-10-01T00:00:00Z, the day of the scenarios
const uint32_t kDayStart = 1790812800;

/**
 * @brief Unix time of a moment of the scenario day.
 *
 * @param[in] h Hours (UTC).
 * @param[in] m Minutes.
 * @param[in] s Seconds.
 * @return The Unix time of hh:mm:ss on 2026-10-01, UTC.
 */
inline uint32_t at(uint32_t h, uint32_t m, uint32_t s) {
    return kDayStart + h * 3600 + m * 60 + s;
}

/// Time between the alarm and the moment the firmware reads the clock
const uint32_t kWakeDelayS = 3;

/**
 * @brief A whole station built from test doubles.
 *
 * By default, it is 14:00:03 (just after an alarm), with a valid clock,
 * a working sensor, storage and Wi-Fi, and an NTP sync one hour ago.
 */
struct Station {
    Config config;                       ///< Default settings
    EventLog log;                        ///< Shared by storage and network
    FakeClock clock;                     ///< Valid, at 14:00:03
    StubSensor sensor;                   ///< Responding
    FakeStorage storage{log};            ///< Working, empty
    MockNetwork network{log};            ///< Wi-Fi and NTP available
    FakePower power;                     ///< Woken by the RTC alarm
    FakeMaintenance maintenance{clock};  ///< Advances the clock
    RetainedState retained;              ///< Synced at 13:00:03

    /// The machine under test, wired to the doubles above
    StateMachine machine{config,
                         {clock, sensor, storage, network, power,
                          maintenance},
                         retained};

    /// Sets the default situation described above

    Station() {
        clock.time = at(14, 0, kWakeDelayS);
        network.ntpTime = clock.time;
        // Synced one hour ago: no sync needed at 14:00
        retained.lastSyncTime = at(13, 0, kWakeDelayS);
    }

    /// Runs one wake-up, from BOOT to SLEEP
    void wake() { machine.run(); }

    /// Sleeps until the programmed alarm, then wakes up
    void wakeAtNextAlarm() {
        clock.time = clock.lastAlarm + kWakeDelayS;
        network.ntpTime = clock.time;
        power.cause = WakeCause::RtcAlarm;
        wake();
    }

    /**
     * @brief Checks the path of the last run.
     *
     * @param[in] expected The expected states, in order.
     * @return true if the last run visited exactly these states.
     */
    bool visited(std::initializer_list<State> expected) const {
        if (machine.visitedCount() != expected.size()) {
            return false;
        }
        size_t i = 0;
        for (State s : expected) {
            if (machine.visited(i++) != s) {
                return false;
            }
        }
        return true;
    }
};
