/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/NoNetwork.h
 *
 * Description:
 * Skeleton network adapter (step A1), replaced by the Wi-Fi adapter in
 * A4. The connection always fails, as when the Wi-Fi is out of reach.
 *
 * Wiring: none.
 * Dependencies: ESP32 Arduino core.
 */

#pragma once

#include <Arduino.h>

#include "INetwork.h"

/**
 * @brief Skeleton network: the connection always fails.
 */
class NoNetwork : public INetwork {
public:
    bool connect(uint32_t /*timeoutS*/) override {
        Serial.println("   no network before step A4: connection failed");
        return false;
    }

    void disconnect() override {}

    bool fetchTime(uint32_t& /*unixTime*/, uint32_t /*timeoutS*/) override {
        return false;
    }
};
