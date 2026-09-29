/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/INetwork.h
 *
 * Description:
 * What the core needs from the network. Step A1 only opens and closes
 * the connection and reads the NTP time; sending rows comes in A4.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstdint>

/**
 * @brief The connection to the home Wi-Fi, the server and NTP.
 *
 * Implemented by the Wi-Fi adapter on the board, and by a mock network
 * in the tests.
 */
class INetwork {
public:
    virtual ~INetwork() = default;

    /**
     * @brief Connects to the home Wi-Fi.
     *
     * Called at most once per wake-up, only when an upload is needed.
     * Must give up after the timeout, to save the battery (N3).
     *
     * @param[in] timeoutS Maximum time to wait for the connection, in seconds.
     * @return true if connected; false if the Wi-Fi was not reachable.
     */
    virtual bool connect(uint32_t timeoutS) = 0;

    /**
     * @brief Closes the connection and turns the Wi-Fi off.
     *
     * Called after each successful connect(), once the network is no
     * longer needed.
     */
    virtual void disconnect() = 0;

    /**
     * @brief Reads the current time from an NTP server.
     *
     * Only called while connected: the daily sync reuses the upload
     * connection (F4).
     *
     * @param[out] unixTime The NTP time (Unix time, UTC), written only on
     *             success.
     * @param[in] timeoutS Maximum time to wait for the answer, in seconds.
     * @return true if the time was received; false otherwise.
     */
    virtual bool fetchTime(uint32_t& unixTime, uint32_t timeoutS) = 0;
};
