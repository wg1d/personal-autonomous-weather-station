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
#include <string>
#include <vector>

#include "EventLog.h"
#include "FakeClock.h"
#include "FakeLog.h"
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
 * By default, it is 14:00:03 (just after an alarm), with a valid clock
 * set by NTP one hour ago, and a working sensor, storage and Wi-Fi.
 */
struct Station {
    Config config;                       ///< Default settings
    EventLog log;                        ///< Shared by storage and network
    FakeClock clock;                     ///< Valid at 14:00:03, set at 13:00
    StubSensor sensor;                   ///< Responding
    FakeStorage storage{log};            ///< Working, empty
    MockNetwork network{log};            ///< Wi-Fi and NTP available
    FakePower power;                     ///< Woken by the RTC alarm
    FakeMaintenance maintenance{clock};  ///< Advances the clock
    FakeLog path;                        ///< States entered by the last wake

    /// The machine under test, wired to the doubles above
    StateMachine machine{config,
                         {clock, sensor, storage, network, power,
                          maintenance, path}};

    /// Sets the default situation described above

    Station() {
        clock.time = at(14, 0, kWakeDelayS);
        network.ntpTime = clock.time;
        // Synced one hour ago: no sync needed at 14:00
        clock.lastSet = at(13, 0, kWakeDelayS);
    }

    /// Runs one wake-up, from BOOT to SLEEP
    void wake() {
        path.states.clear();
        machine.run();
    }

    /// Sleeps until the programmed alarm, then wakes up
    void wakeAtNextAlarm() {
        clock.time = clock.lastAlarm + kWakeDelayS;
        network.ntpTime = clock.time;
        power.cause = WakeCause::RtcAlarm;
        wake();
    }

    /**
     * @brief The rows received by the server, in order.
     *
     * @return One text per row, without the header line of each request
     *         and without the line break.
     */
    std::vector<std::string> receivedRows() const {
        std::vector<std::string> rows;
        for (const std::string& request : network.requests) {
            size_t start = request.find('\n') + 1;  // after the header
            while (start < request.size()) {
                size_t end = request.find("\r\n", start);
                rows.push_back(request.substr(start, end - start));
                start = end + 2;
            }
        }
        return rows;
    }

    /**
     * @brief Checks the path of the last run.
     *
     * @param[in] expected The expected states, in order.
     * @return true if the last run visited exactly these states.
     */
    bool visited(std::initializer_list<State> expected) const {
        std::vector<std::string> names;
        for (State s : expected) {
            names.push_back(stateName(s));
        }
        return path.states == names;
    }
};
