/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/SdStorage.h
 *
 * Description:
 * Storage adapter for the SD card: appends each row to the CSV file
 * /measurements_v1.csv, and gives back the rows after the upload cursor,
 * kept in /upload.idx. The card module is powered only while it is used.
 *
 * Wiring:
 * - SD card: 5V -> VCC, GND -> GND, Pin 19 -> MISO, Pin 23 -> MOSI,
 *            Pin 18 -> SCLK, Pin 5 -> CS,
 *            Pin 13 -> OFF (10k pull-down resistor to GND)
 * Dependencies: ESP32 Arduino core (SD, FS), lib/core (CSV format).
 */

#pragma once

#include <Arduino.h>
#include <SD.h>

#include "CsvFormat.h"
#include "IStorage.h"

/// Chip select of the SD card module (SPI)
const uint8_t kSdCsPin = 5;

/// Power switch of the SD card module: HIGH turns it on
const uint8_t kSdPowerPin = 13;

/// File holding the upload cursor: the position, in bytes, of the first
/// row of the CSV file that the server has not acknowledged
const char kCursorFileName[] = "/upload.idx";

/// Time for the card to power up before it can be used. The SD
/// specification allows up to 35 ms of supply ramp-up, then 1 ms of
/// stable supply; the module adds a regulator and capacitors, with no
/// datasheet. 100 ms is a margin, kept from the PoC, not a measured value.
const uint32_t kSdPowerUpMs = 100;

/**
 * @brief Storage adapter for the SD card.
 *
 * If the card is missing or cannot be written, append() reports it and
 * returns false: the row is lost, but the station keeps its schedule.
 */
class SdStorage : public IStorage {
public:
    bool append(const Record& record) override {
        char row[kCsvRowSize];
        if (!formatCsvRow(record, row, sizeof(row))) {
            Serial.println("   row too long for the buffer");
            return false;
        }
        bool stored = mount() && write(row);
        unmount();
        Serial.printf("   %s: %s\n", stored ? "stored" : "NOT stored", row);
        return stored;
    }

    size_t readUnsent(char* buffer, size_t size) override {
        size_t length = mount() ? read(buffer, size) : 0;
        unmount();
        return length;
    }

    bool markSent(size_t length) override {
        bool saved = mount() && saveCursor(unsentStart_ + length);
        unmount();
        return saved;
    }

private:
    // Powers the card module on and mounts the card. The module stays off
    // during deep sleep, to save the battery.
    bool mount() {
        pinMode(kSdPowerPin, OUTPUT);
        digitalWrite(kSdPowerPin, HIGH);
        delay(kSdPowerUpMs);
        if (!SD.begin(kSdCsPin)) {
            Serial.println("   SD card not found");
            return false;
        }
        return true;
    }

    void unmount() {
        SD.end();
        digitalWrite(kSdPowerPin, LOW);
    }

    // Appends the row, after the header if the file is new
    bool write(const char* row) {
        bool newFile = !SD.exists(kCsvFileName);
        File file = SD.open(kCsvFileName, FILE_APPEND);
        if (!file) {
            Serial.println("   cannot open the CSV file");
            return false;
        }
        if (newFile) {
            file.println(kCsvHeader);
        }
        // println() returns the number of bytes written: 0 means failure
        bool written = file.println(row) > 0;
        file.close();
        return written;
    }

    // Reads complete rows from the cursor, as many as fit in the buffer
    size_t read(char* buffer, size_t size) {
        // Check first: opening a missing file prints an error of the
        // SD library, although it is a normal case here
        if (!SD.exists(kCsvFileName)) {
            return 0;  // no file yet: nothing to send
        }
        File file = SD.open(kCsvFileName, FILE_READ);
        if (!file) {
            return 0;
        }
        uint32_t cursor = loadCursor();
        if (cursor == 0) {
            // Start of the file: skip the header line, which the core
            // adds to each request itself
            while (file.available() && file.read() != '\n') {
            }
            cursor = file.position();
        }
        file.seek(cursor);
        size_t length = file.read(reinterpret_cast<uint8_t*>(buffer), size);
        file.close();

        // Keep complete rows only: cut after the last line break
        while (length > 0 && buffer[length - 1] != '\n') {
            --length;
        }
        // markSent() moves the cursor from here
        unsentStart_ = cursor;
        return length;
    }

    // The cursor is stored as text, for example "1234". A missing file
    // means that nothing was sent yet: everything is sent again, and the
    // server ignores the rows it already has.
    uint32_t loadCursor() {
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

    bool saveCursor(uint32_t cursor) {
        // FILE_WRITE replaces the previous content
        File file = SD.open(kCursorFileName, FILE_WRITE);
        if (!file) {
            Serial.println("   cannot save the upload cursor");
            return false;
        }
        bool saved = file.print(cursor) > 0;
        file.close();
        return saved;
    }

    uint32_t unsentStart_ = 0;  // where the rows of the last read start
};
