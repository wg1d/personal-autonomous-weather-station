/*
 * Project: Personal Autonomous Weather Station
 * Tool: wifi_signal.ino
 *
 * Description:
 * Measures the strength of the Wi-Fi signal (RSSI) every second, to check
 * the range at the place of the outdoor station before it is built.
 * The board connects to the home Wi-Fi and shows the signal:
 * - on the serial monitor, with its IP address at start-up;
 * - on a web page at this address, which reloads itself every second:
 *   a phone on the same Wi-Fi shows it in the garden.
 *
 * The board is powered by a USB power bank in the garden. The Wi-Fi name
 * and password are those of the station, read from firmware/paws/include/
 * secrets.h.
 *
 * Dependencies: Arduino core for the ESP32 (WiFi, WebServer).
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include "secrets.h"

// The RSSI is in dBm, a negative number: the closer to 0, the stronger
// the signal. Below a threshold, the signal gets the next verdict.
const int kVeryGoodDbm = -67;
const int kGoodDbm = -75;
const int kWeakDbm = -85;

const unsigned long kPeriodMs = 1000;

WebServer server(80);

int lastRssi = 0;
int weakestRssi = 0;
int strongestRssi = -127;
unsigned long lastMeasureMs = 0;

const char* verdict(int rssi) {
    if (rssi >= kVeryGoodDbm) return "very good";
    if (rssi >= kGoodDbm) return "good";
    if (rssi >= kWeakDbm) return "weak, enough for small uploads";
    return "too weak: antenna or repeater needed";
}

// The page reloads itself every second (meta refresh)
void showPage() {
    String page =
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        "<meta http-equiv='refresh' content='1'>"
        "<title>Wi-Fi signal</title></head>"
        "<body style='font-family:sans-serif;text-align:center'>"
        "<h1>" + String(lastRssi) + " dBm</h1>"
        "<p>" + verdict(lastRssi) + "</p>"
        "<p>strongest " + String(strongestRssi) + " dBm, weakest " +
        String(weakestRssi) + " dBm since start-up</p>"
        "</body></html>";
    server.send(200, "text/html", page);
}

void setup() {
    Serial.begin(115200);

    WiFi.mode(WIFI_STA);
    WiFi.begin(kWifiSsid, kWifiPassword);
    Serial.print("Connecting to the Wi-Fi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    Serial.print("Connected. Open this address on a phone: http://");
    Serial.println(WiFi.localIP());

    server.on("/", showPage);
    server.begin();
}

void loop() {
    server.handleClient();

    if (millis() - lastMeasureMs < kPeriodMs) return;
    lastMeasureMs = millis();

    // When the connection is lost, the ESP32 reconnects by itself
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Not connected");
        return;
    }

    lastRssi = WiFi.RSSI();
    if (lastRssi < weakestRssi) weakestRssi = lastRssi;
    if (lastRssi > strongestRssi) strongestRssi = lastRssi;
    Serial.printf("%d dBm: %s\n", lastRssi, verdict(lastRssi));
}
