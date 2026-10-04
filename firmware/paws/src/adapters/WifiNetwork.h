/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/WifiNetwork.h
 *
 * Description:
 * Network adapter for the home Wi-Fi: connects as a station, sends the
 * rows to the server with an HTTP POST request, reads the time from an
 * NTP server, and turns the Wi-Fi off afterwards.
 *
 * Wiring: none (Wi-Fi is built into the ESP32).
 * Dependencies: ESP32 Arduino core (WiFi, HTTPClient, SNTP).
 */

#pragma once

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <sys/time.h>
#include <time.h>

#include "INetwork.h"

/// NTP servers, chosen among the closest ones by the pool
const char kNtpServer[] = "pool.ntp.org";

/// Time between two checks of the Wi-Fi connection
const uint32_t kWifiPollMs = 100;

/// Maximum time to wait for the answer of the server
const uint32_t kServerTimeoutMs = 10000;

/// Wi-Fi channel and router address (BSSID) of the last connection, kept
/// in RTC memory across deep sleep. Channel 0 means "not known": after a
/// power loss, or after a failed connection.
RTC_DATA_ATTR static int32_t lastWifiChannel = 0;
RTC_DATA_ATTR static uint8_t lastWifiBssid[6];

/**
 * @brief Network adapter for the home Wi-Fi.
 *
 * Each failure (Wi-Fi out of reach, NTP not answering) is reported on
 * the serial port and returned to the core, which keeps its schedule.
 */
class WifiNetwork : public INetwork {
public:
    /**
     * @brief Creates the adapter for a Wi-Fi network and a server.
     *
     * @param[in] ssid Name of the network.
     * @param[in] password Password of the network.
     * @param[in] serverUrl Address of the measurements endpoint, such as
     *            "http://192.168.1.15:8080/api/v1/measurements".
     */
    WifiNetwork(const char* ssid, const char* password,
                const char* serverUrl)
        : ssid_(ssid), password_(password), serverUrl_(serverUrl) {}

    bool connect(uint32_t timeoutS) override {
        WiFi.mode(WIFI_STA);
        if (lastWifiChannel != 0) {
            // Go straight to the router of the last connection, instead
            // of scanning every channel to find it
            WiFi.begin(ssid_, password_, lastWifiChannel, lastWifiBssid);
        } else {
            WiFi.begin(ssid_, password_);
        }

        uint32_t start = millis();
        while (WiFi.status() != WL_CONNECTED) {
            if (millis() - start > timeoutS * 1000) {
                Serial.println("   Wi-Fi not reachable");
                // The router may have changed channel: scan again next time
                lastWifiChannel = 0;
                disconnect();
                return false;
            }
            delay(kWifiPollMs);
        }
        Serial.printf("   Wi-Fi connected in %lu ms\n",
                      static_cast<unsigned long>(millis() - start));

        lastWifiChannel = WiFi.channel();
        memcpy(lastWifiBssid, WiFi.BSSID(), sizeof(lastWifiBssid));
        return true;
    }

    void disconnect() override {
        // Turn the radio off: it is by far the largest consumer (N3)
        WiFi.disconnect(true);
        WiFi.mode(WIFI_OFF);
    }

    bool send(const char* data, size_t length) override {
        HTTPClient http;
        http.begin(serverUrl_);
        http.setTimeout(kServerTimeoutMs);
        http.addHeader("Content-Type", "text/csv");
        int status = http.POST(
            reinterpret_cast<uint8_t*>(const_cast<char*>(data)), length);

        // The server answers with a short summary, such as
        // {"received": 4, "inserted": 4, "duplicates": 0}: print it to
        // help debugging, without copying it into a String
        char answer[96] = "";
        int answerSize = http.getSize();  // -1 if the server did not say
        if (status > 0 && answerSize > 0) {
            // Read exactly the announced size: readBytes() would otherwise
            // wait for the timeout to fill the whole buffer
            size_t toRead = answerSize < static_cast<int>(sizeof(answer))
                                ? answerSize
                                : sizeof(answer) - 1;
            size_t read = http.getStreamPtr()->readBytes(answer, toRead);
            answer[read] = '\0';
        }
        http.end();

        // A negative status is a connection error, not an HTTP status
        Serial.printf("   sent %lu bytes, server answered %d %s\n",
                      static_cast<unsigned long>(length), status, answer);
        return status >= 200 && status < 300;
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
    const char* serverUrl_;
};
