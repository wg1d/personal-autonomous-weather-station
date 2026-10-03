/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/SdCard.h
 *
 * Description:
 * The SD card module, shared by the storage adapter and the maintenance
 * mode: its pins, its files, and how to power it on and off.
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

/// Chip select of the SD card module (SPI)
const uint8_t kSdCsPin = 5;

/// Power switch of the SD card module: HIGH turns it on
const uint8_t kSdPowerPin = 13;

/// Time for the card to power up before it can be used. The SD
/// specification allows up to 35 ms of supply ramp-up, then 1 ms of
/// stable supply; the module adds a regulator and capacitors, with no
/// datasheet. 100 ms is a margin, kept from the PoC, not a measured value.
const uint32_t kSdPowerUpMs = 100;

/// File holding the upload cursor: the position, in bytes, of the first
/// row of the CSV file that the server has not acknowledged
const char kCursorFileName[] = "/upload.idx";

/**
 * @brief Powers the card module on and mounts the card.
 *
 * The module stays off during deep sleep, to save the battery.
 *
 * @return true if the card is ready; false if it is missing.
 */
inline bool sdMount() {
    pinMode(kSdPowerPin, OUTPUT);
    digitalWrite(kSdPowerPin, HIGH);
    delay(kSdPowerUpMs);
    if (!SD.begin(kSdCsPin)) {
        Serial.println("   SD card not found");
        return false;
    }
    return true;
}

/**
 * @brief Reads the upload cursor from the mounted card.
 *
 * A missing file means that nothing was sent yet: everything is sent
 * again, and the server ignores the rows it already has.
 *
 * @return The cursor, stored as text such as "1234"; 0 if there is none.
 */
inline uint32_t sdLoadCursor() {
    if (!SD.exists(kCursorFileName)) {
        return 0;
    }
    File file = SD.open(kCursorFileName, FILE_READ);
    if (!file) {
        return 0;
    }
    uint32_t cursor = static_cast<uint32_t>(file.parseInt());
    file.close();
    return cursor;
}

/**
 * @brief Unmounts the card and powers the module off.
 */
inline void sdUnmount() {
    SD.end();
    digitalWrite(kSdPowerPin, LOW);
}
