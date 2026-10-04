/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/AccessPointMaintenance.h
 *
 * Description:
 * Maintenance mode (F5): the ESP32 starts its own Wi-Fi network (an
 * access point) and a web page, to download or delete the measurements
 * of the SD card, or download its log, from a phone, for a limited time.
 *
 * Wiring: none (Wi-Fi is built into the ESP32; SD card: see SdCard.h).
 * Dependencies: ESP32 Arduino core (WiFi, WebServer, SD), lib/core (CSV
 * file name), SdCard.h.
 */

#pragma once

#include <Arduino.h>
#include <SD.h>
#include <WebServer.h>
#include <WiFi.h>

#include "Console.h"
#include "CsvFormat.h"
#include "IMaintenance.h"
#include "SdCard.h"

/// The maintenance page. The style gives large buttons for a phone, and
/// the icon is a sunflower drawn from an emoji, so that no image file is
/// needed. The %s and %lu are filled by sendPage(): a message, the state
/// of the card, "disabled" twice when there is nothing to download or
/// delete, "disabled" once more when there is no log, the firmware
/// version, then twice the time left, which a small script counts down;
/// at 0, it tells that the access point is closed. The script also puts
/// the address back to "/", so that a message such as "Measurements
/// deleted." is not shown again when the page is reloaded.
const char kMaintenancePage[] =
    "<html><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width'>"
    "<title>PAWS maintenance</title>"
    "<link rel='icon' href=\"data:image/svg+xml,<svg xmlns="
    "'http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em'"
    " font-size='90'>&#127803;</text></svg>\">"
    "<style>body{font-family:Arial,sans-serif;text-align:center;"
    "padding:20px}h1{font-size:1.6em}"
    "button{width:100%%;max-width:320px;padding:15px;font-size:18px;"
    "margin:8px 0;border:none;border-radius:8px;color:white}"
    "small{color:#888}"
    ".download{background:#4CAF50}.log{background:#2196F3}"
    ".delete{background:#f44336}"
    "button:disabled{background:#bbb}</style></head>"
    "<body><h1>&#127803; PAWS maintenance</h1>"
    "<p><b>%s</b></p><p>%s</p>"
    "<form action='/download'>"
    "<button class='download' %s>Download the measurements</button>"
    "</form>"
    "<form action='/log'>"
    "<button class='log' %s>Download the log</button></form>"
    "<form action='/delete' method='POST' onsubmit=\"return confirm("
    "'Delete all the measurements, including those not uploaded yet?')\">"
    "<button class='delete' type='submit' %s>Delete the measurements"
    "</button></form>"
    "<p id='info'>This page stays available for <span id='left'>%lu"
    "</span> s.</p><p><small>Firmware %s</small></p>"
    "<script>history.replaceState(null,'','/');"
    "var left=%lu;setInterval(function(){"
    "if(left>0){document.getElementById('left').textContent=--left;}"
    "else{document.getElementById('info').innerHTML='<b>The access point"
    " is now closed.</b> The station went back to its normal cycle. To "
    "start a new session, press the button of the station again.';"
    "document.querySelectorAll('button').forEach(function(b){"
    "b.disabled=true;});}},1000);</script>"
    "</body></html>";

/**
 * @brief Maintenance mode: access point and web page.
 *
 * The session lasts the given duration, whether a phone connects or not,
 * then the access point is turned off.
 */
class AccessPointMaintenance : public IMaintenance {
public:
    /**
     * @brief Creates the maintenance mode with its Wi-Fi network.
     *
     * @param[in,out] card The SD card module, shared with the storage.
     * @param[in] ssid Name of the network started by the station.
     * @param[in] password Its password, at least 8 characters (WPA2).
     * @param[in] version Firmware version, shown on the page.
     */
    AccessPointMaintenance(SdCard& card, const char* ssid,
                           const char* password, const char* version)
        : card_(card), ssid_(ssid), password_(password), version_(version) {}

    void run(uint32_t durationS) override {
        // The card stays powered for the whole session, and until the end
        // of the wake-up: the storage uses it right after
        cardReady_ = card_.mount();

        WiFi.mode(WIFI_AP);
        WiFi.softAP(ssid_, password_);
        console.printf("   access point \"%s\" started, page: http://",
                      ssid_);
        console.println(WiFi.softAPIP());

        start_ = millis();
        durationMs_ = durationS * 1000;

        // Each address of the page calls one function of this class
        WebServer server(80);
        server.on("/", HTTP_GET, [this, &server]() {
            // After a deletion, the station comes back here with a
            // parameter that says what happened (see deleteMeasurements())
            if (server.arg("message") == "deleted") {
                sendPage(server, "Measurements deleted.");
            } else if (server.arg("message") == "nothing") {
                sendPage(server, "Nothing to delete.");
            } else {
                sendPage(server, "");
            }
        });
        server.on("/download", HTTP_GET, [this, &server]() {
            sendMeasurements(server);
        });
        server.on("/log", HTTP_GET, [this, &server]() {
            sendLog(server);
        });
        server.on("/delete", HTTP_POST, [this, &server]() {
            deleteMeasurements(server);
        });
        // Any other address, such as the /favicon.ico that browsers ask
        // for: "not found", without an error message from the library
        server.onNotFound([&server]() {
            server.send(404, "text/plain", "Not found");
        });
        server.begin();

        // Serve the requests until the end of the session
        while (millis() - start_ < durationMs_) {
            server.handleClient();
            delay(2);
        }

        server.stop();
        // Turning the Wi-Fi off also stops the access point
        WiFi.mode(WIFI_OFF);
        console.println("   access point stopped");
    }

private:
    // Size of the measurement file, 0 if there is none
    size_t fileSize() {
        if (!cardReady_ || !SD.exists(kCsvFileName)) {
            return 0;
        }
        File file = SD.open(kCsvFileName, FILE_READ);
        size_t size = file.size();
        file.close();
        return size;
    }

    void sendPage(WebServer& server, const char* message) {
        // What is on the card, and how much the server does not have yet:
        // the bytes after the upload cursor
        char state[96];
        size_t size = fileSize();
        bool empty = size == 0;
        if (!cardReady_) {
            snprintf(state, sizeof(state), "SD card not found.");
        } else if (empty) {
            snprintf(state, sizeof(state), "No measurements on the card.");
        } else {
            uint32_t cursor = card_.loadCursor(kCursorFileName);
            size_t unsent = cursor < size ? size - cursor : 0;
            snprintf(state, sizeof(state),
                     "%lu KB of measurements on the card, %lu KB not "
                     "uploaded yet.",
                     static_cast<unsigned long>((size + 1023) / 1024),
                     static_cast<unsigned long>((unsent + 1023) / 1024));
        }

        unsigned long secondsLeft = (durationMs_ - (millis() - start_)) / 1000;
        const char* disabled = empty ? "disabled" : "";
        bool noLog = !cardReady_ || !SD.exists(kLogFileName);
        const char* logDisabled = noLog ? "disabled" : "";

        char page[sizeof(kMaintenancePage) + 200];
        snprintf(page, sizeof(page), kMaintenancePage, message, state,
                 disabled, logDisabled, disabled, secondsLeft, version_,
                 secondsLeft);
        server.send(200, "text/html", page);
    }

    void sendMeasurements(WebServer& server) {
        if (fileSize() == 0) {
            sendPage(server, "No measurements to download.");
            return;
        }
        File file = SD.open(kCsvFileName, FILE_READ);
        // "attachment": the phone saves the file instead of showing it
        server.sendHeader("Content-Disposition",
                          "attachment; filename=measurements_v1.csv");
        server.streamFile(file, "text/csv");
        file.close();
        console.println("   measurements downloaded");
    }

    void sendLog(WebServer& server) {
        if (!cardReady_ || !SD.exists(kLogFileName)) {
            sendPage(server, "No log on the card.");
            return;
        }
        File file = SD.open(kLogFileName, FILE_READ);
        server.sendHeader("Content-Disposition",
                          "attachment; filename=log.txt");
        server.streamFile(file, "text/plain");
        file.close();
        console.println("   log downloaded");
    }

    void deleteMeasurements(WebServer& server) {
        bool deleted = false;
        if (fileSize() > 0) {
            // Remove the cursor too: it points into the deleted file
            SD.remove(kCsvFileName);
            SD.remove(kCursorFileName);
            deleted = true;
            console.println("   measurements deleted");
        }
        // Send the phone back to the main page (code 303, "see other"),
        // instead of answering here: reloading the page then cannot send
        // the deletion a second time
        server.sendHeader("Location", deleted ? "/?message=deleted"
                                              : "/?message=nothing");
        server.send(303);
    }

    SdCard& card_;
    const char* ssid_;
    const char* password_;
    const char* version_;
    bool cardReady_ = false;
    uint32_t start_ = 0;       // millis() when the session started
    uint32_t durationMs_ = 0;  // length of the session
};
