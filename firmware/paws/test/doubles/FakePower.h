/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/FakePower.h
 *
 * Description:
 * Fake power management: the test chooses the wake-up cause, and
 * sleep() records the plan instead of stopping the program.
 *
 * Dependencies: lib/ports.
 */

#pragma once

#include "IPower.h"

/**
 * @brief Fake power management: records the plan instead of sleeping.
 */
class FakePower : public IPower {
public:
    WakeCause cause = WakeCause::RtcAlarm;  ///< Returned by wakeCause()

    SleepPlan lastPlan;  ///< Plan of the last call to sleep()
    int sleepCount = 0;  ///< Number of calls to sleep()

    WakeCause wakeCause() override { return cause; }

    void sleep(const SleepPlan& plan) override {
        lastPlan = plan;
        ++sleepCount;
    }
};
