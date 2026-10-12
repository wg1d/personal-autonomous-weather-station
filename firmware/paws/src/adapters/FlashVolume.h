/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/SdCard.h
 *
 * Description:
 * The SD card module, shared by the storage adapter and the maintenance
 * mode: its pins, its files, and its power. The card is mounted at its
 * first use in a wake-up, and stays mounted until the end of the
 * wake-up, so that it is initialized only once.
 *
 * Wiring:
 * - SD card: 5V -> VCC, GND -> GND, Pin 19 -> MISO, Pin 23 -> MOSI,
 *            Pin 18 -> SCLK, Pin 5 -> CS,
 *            Pin 13 -> OFF (10k pull-down resistor to GND)
 * Dependencies: ESP32 Arduino core (SD, FS).
 */

#pragma once

#include <Arduino.h>
#include <SD.h>

#include "Console.h"

/// Chip select of the SD card module (SPI)
const uint8_t kSdCsPin = 5;

/// Power switch of the SD card module: HIGH turns it on
const uint8_t kSdPowerPin = 13;

/// Time for the card to power up before it can be used. The SD
/// specification allows up to 35 ms of supply ramp-up, then 1 ms of
/// stable supply; the module adds a regulator and capacitors, with no
/// datasheet. 100 ms is a margin, kept from the PoC, not a measured value.
const uint32_t kSdPowerUpMs = 100;

/// File holding the upload cursor of the measurements: the position, in
/// bytes, of the first row of the CSV file that the server has not
/// acknowledged
const char kCursorFileName[] = "/upload.idx";

/// Log of the wake-ups: what the station printed on the serial port
const char kLogFileName[] = "/log.txt";

/// Previous log file, kept when the log reaches its maximum size
const char kOldLogFileName[] = "/log.old";

/// Upload cursor of the log, as for the measurements
const char kLogCursorFileName[] = "/log.idx";

/**
 * @brief The SD card module: power and mounting.
 *
 * One object is created by main.cpp and given to the adapters that use
 * the card, so that they share its state.
 */
class SdCard {
public:
    /**
     * @brief Powers the module on and mounts the card, if not done yet.
     *
     * The module stays off during deep sleep, to save the battery.
     *
     * @return true if the card is ready; false if it is missing.
     */
    bool mount() {
        if (mounted_) {
            return true;
        }
        pinMode(kSdPowerPin, OUTPUT);
        digitalWrite(kSdPowerPin, HIGH);
        delay(kSdPowerUpMs);
        if (!SD.begin(kSdCsPin)) {
            console.println("   SD card not found");
            digitalWrite(kSdPowerPin, LOW);
            return false;
        }
        mounted_ = true;
        return true;
    }

    /**
     * @brief Unmounts the card and powers the module off.
     */
    void unmount() {
        if (mounted_) {
            SD.end();
            mounted_ = false;
        }
        digitalWrite(kSdPowerPin, LOW);
    }

    /**
     * @brief Tells whether the card is mounted.
     *
     * @return true between a successful mount() and unmount().
     */
    bool isMounted() const { return mounted_; }

    /**
     * @brief Reads an upload cursor from the card, which must be mounted.
     *
     * A missing file means that nothing was sent yet: everything is sent
     * again, and the server ignores the rows it already has.
     *
     * @param[in] fileName The cursor file, such as kCursorFileName.
     * @return The cursor, stored as text such as "1234"; 0 if there is
     *         none.
     */
    uint32_t loadCursor(const char* fileName) {
        if (!SD.exists(fileName)) {
            return 0;
        }
        File file = SD.open(fileName, FILE_READ);
        if (!file) {
            return 0;
        }
        uint32_t cursor = static_cast<uint32_t>(file.parseInt());
        file.close();
        return cursor;
    }

private:
    bool mounted_ = false;
};
