/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/WifiNetwork.h
 *
 * Description:
 * Network adapter for the home Wi-Fi: connects as a station, reads the
 * time from an NTP server, and turns the Wi-Fi off afterwards. Sending
 * the rows to the server comes in the second part of step A4.
 *
 * Wiring: none (Wi-Fi is built into the ESP32).
 * Dependencies: ESP32 Arduino core (WiFi, SNTP).
 */

#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <sys/time.h>
#include <time.h>

#include "INetwork.h"

/// NTP servers, chosen among the closest ones by the pool
const char kNtpServer[] = "pool.ntp.org";

/// Time between two checks of the Wi-Fi connection
const uint32_t kWifiPollMs = 100;

/**
 * @brief Network adapter for the home Wi-Fi.
 *
 * Each failure (Wi-Fi out of reach, NTP not answering) is reported on
 * the serial port and returned to the core, which keeps its schedule.
 */
class WifiNetwork : public INetwork {
public:
    /**
     * @brief Creates the adapter for a Wi-Fi network.
     *
     * @param[in] ssid Name of the network.
     * @param[in] password Password of the network.
     */
    WifiNetwork(const char* ssid, const char* password)
        : ssid_(ssid), password_(password) {}

    bool connect(uint32_t timeoutS) override {
        WiFi.mode(WIFI_STA);
        WiFi.begin(ssid_, password_);

        uint32_t start = millis();
        while (WiFi.status() != WL_CONNECTED) {
            if (millis() - start > timeoutS * 1000) {
                Serial.println("   Wi-Fi not reachable");
                disconnect();
                return false;
            }
            delay(kWifiPollMs);
        }
        Serial.printf("   Wi-Fi connected in %lu ms\n",
                      static_cast<unsigned long>(millis() - start));
        return true;
    }

    void disconnect() override {
        // Turn the radio off: it is by far the largest consumer (N3)
        WiFi.disconnect(true);
        WiFi.mode(WIFI_OFF);
    }

    bool fetchTime(uint32_t& unixTime, uint32_t timeoutS) override {
        // The system clock of the ESP32 keeps running during deep sleep.
        // Reset it, so that getLocalTime() waits for a real NTP answer
        // instead of returning the old system time at once.
        timeval zero = {0, 0};
        settimeofday(&zero, nullptr);

        // Offsets 0: we want UTC, without daylight saving time
        configTime(0, 0, kNtpServer);
        tm received;
        if (!getLocalTime(&received, timeoutS * 1000)) {
            Serial.println("   NTP not answering");
            return false;
        }
        unixTime = static_cast<uint32_t>(time(nullptr));
        Serial.println("   NTP time received");
        return true;
    }

private:
    const char* ssid_;
    const char* password_;
};
