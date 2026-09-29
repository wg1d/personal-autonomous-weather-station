/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/Config.h
 *
 * Description:
 * The settings used by the core. The defaults are the values of the
 * Phase 4 design; main.cpp and the tests can change them (for example a
 * short interval for a demo on the bench).
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstdint>

/**
 * @brief The settings of the core, in seconds.
 *
 * The default values are those of the Phase 4 design. main.cpp and the
 * tests can change them, for example to use a short interval for a demo
 * on the bench.
 */
struct Config {
    /// Time between two measurements, on a fixed UTC grid (F1)
    uint32_t measurementIntervalS = 15 * 60;

    /// Time between two uploads (F3)
    uint32_t uploadPeriodS = 60 * 60;

    /// Maximum age of the last NTP sync (F4)
    uint32_t syncPeriodS = 24 * 60 * 60;

    /// Delay between the planned alarm and the safety timer (N2). It lets
    /// the RTC alarm always fire first, despite the timer's drift.
    uint32_t safetyMarginS = 60;

    /// Duration of the access point session (F5)
    uint32_t maintenanceDurationS = 3 * 60;

    /// Maximum time to wait for the Wi-Fi connection
    uint32_t wifiTimeoutS = 10;

    /// Maximum time to wait for the NTP answer
    uint32_t ntpTimeoutS = 5;
};
