/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/MockNetwork.h
 *
 * Description:
 * Mock network: records each call in the shared log ("connect",
 * "disconnect", "send", "ntp") and the requests sent to the server, and
 * lets the test choose whether the Wi-Fi, the server and NTP work.
 *
 * Dependencies: lib/ports, EventLog.h.
 */

#pragma once

#include <cstdint>
#include <string>
#include <vector>

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
    bool serverWorks = true;    ///< false simulates a server error
    bool ntpAvailable = true;   ///< false simulates NTP not answering
    uint32_t ntpTime = 0;       ///< Time returned by fetchTime()

    bool connected = false;     ///< Whether a connection is open

    /// The requests of measurements the server accepted, oldest first
    std::vector<std::string> requests;

    /// The requests of log lines the server accepted, oldest first
    std::vector<std::string> logRequests;

    bool connect(uint32_t /*timeoutS*/) override {
        log_.add("connect");
        connected = wifiAvailable;
        return connected;
    }

    void disconnect() override {
        log_.add("disconnect");
        connected = false;
    }

    bool send(DataKind kind, const char* data, size_t length) override {
        log_.add(connected ? "send" : "send-while-disconnected");
        if (!connected || !serverWorks) {
            return false;
        }
        if (kind == DataKind::Log) {
            logRequests.push_back(std::string(data, length));
        } else {
            requests.push_back(std::string(data, length));
        }
        return true;
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
