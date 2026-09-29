/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/IMaintenance.h
 *
 * Description:
 * What the core needs from the maintenance mode (F5): run the access
 * point and its web page for a given duration, then return.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstdint>

/**
 * @brief The maintenance mode: an access point and a web page to
 *        download or delete the data from a phone (F5).
 *
 * Implemented by the access point adapter on the board, and by a fake in
 * the tests.
 */
class IMaintenance {
public:
    virtual ~IMaintenance() = default;

    /**
     * @brief Runs one maintenance session, then returns.
     *
     * Called when the button woke the station up. Blocks during the
     * session, and turns the access point off before returning.
     *
     * @param[in] durationS Maximum duration of the session, in seconds.
     */
    virtual void run(uint32_t durationS) = 0;
};
