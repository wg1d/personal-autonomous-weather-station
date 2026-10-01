/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/ILog.h
 *
 * Description:
 * Where the core reports the states it goes through, so that a person
 * (on the serial port) or a test can follow the path of a wake-up.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

/**
 * @brief The log of the states entered by the state machine.
 *
 * Implemented by a serial log on the board, and by a fake log in the
 * tests, which keeps the names so that the test can check the path.
 */
class ILog {
public:
    virtual ~ILog() = default;

    /**
     * @brief Records that the machine entered a state.
     *
     * @param[in] name The name of the state, such as "BOOT".
     */
    virtual void stateEntered(const char* name) = 0;
};
