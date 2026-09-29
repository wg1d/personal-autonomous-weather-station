/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/FakeMaintenance.h
 *
 * Description:
 * Fake maintenance mode: returns at once, but advances the fake clock by
 * the session duration, as the real session would.
 *
 * Dependencies: lib/ports, FakeClock.h.
 */

#pragma once

#include <cstdint>

#include "FakeClock.h"
#include "IMaintenance.h"

/**
 * @brief Fake maintenance mode: advances the clock by the session.
 */
class FakeMaintenance : public IMaintenance {
public:
    /**
     * @brief Creates the fake.
     *
     * @param[in,out] clock The clock advanced by each session.
     */
    explicit FakeMaintenance(FakeClock& clock) : clock_(clock) {}

    int runCount = 0;  ///< Number of sessions run

    void run(uint32_t durationS) override {
        ++runCount;
        clock_.advance(durationS);
    }

private:
    FakeClock& clock_;
};
