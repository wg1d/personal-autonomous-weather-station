/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/MockNetwork.h
 *
 * Description:
 * Mock network: records each call in the shared log ("connect",
 * "disconnect", "ntp"), and lets the test choose whether the Wi-Fi and
 * NTP work and which time NTP returns.
 *
 * Dependencies: lib/ports, EventLog.h.
 */

#pragma once

#include <cstdint>

#include "EventLog.h"
#include "INetwork.h"

/**
 * @brief Mock network: logs each call, and fails when the test says so.
 */
class MockNetwork : public INetwork {
public:
    /**
     * @brief Creates a network where the Wi-Fi and NTP work.
     *
     * @param[in,out] log The shared log, where each call is added.
     */
    explicit MockNetwork(EventLog& log) : log_(log) {}

    bool wifiAvailable = true;  ///< false simulates the Wi-Fi out of reach
    bool ntpAvailable = true;   ///< false simulates NTP not answering
    uint32_t ntpTime = 0;       ///< Time returned by fetchTime()

    bool connected = false;     ///< Whether a connection is open

    bool connect(uint32_t /*timeoutS*/) override {
        log_.add("connect");
        connected = wifiAvailable;
        return connected;
    }

    void disconnect() override {
        log_.add("disconnect");
        connected = false;
    }

    bool fetchTime(uint32_t& unixTime, uint32_t /*timeoutS*/) override {
        log_.add(connected ? "ntp" : "ntp-while-disconnected");
        if (!connected || !ntpAvailable) {
            return false;
        }
        unixTime = ntpTime;
        return true;
    }

private:
    EventLog& log_;
};
