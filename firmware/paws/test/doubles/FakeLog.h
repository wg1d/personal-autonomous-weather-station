/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/FakeLog.h
 *
 * Description:
 * Fake log: keeps the names of the states entered, so that a test can
 * check the path of a wake-up.
 *
 * Dependencies: lib/ports.
 */

#pragma once

#include <string>
#include <vector>

#include "ILog.h"

/**
 * @brief Fake log: keeps the names of the states entered, in order.
 */
class FakeLog : public ILog {
public:
    std::vector<std::string> states;  ///< The states entered, in order

    void stateEntered(const char* name) override { states.push_back(name); }
};
