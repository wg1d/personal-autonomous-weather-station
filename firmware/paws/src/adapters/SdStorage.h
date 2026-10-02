/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/SdStorage.h
 *
 * Description:
 * Storage adapter for the SD card: appends each row to the CSV file
 * /measurements_v1.csv. The card module is powered only while it is
 * used.
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

        // The module stays off during deep sleep, to save the battery:
        // turn it on only for this write
        pinMode(kSdPowerPin, OUTPUT);
        digitalWrite(kSdPowerPin, HIGH);
        delay(kSdPowerUpMs);

        bool stored = write(row);

        SD.end();
        digitalWrite(kSdPowerPin, LOW);

        Serial.printf("   %s: %s\n", stored ? "stored" : "NOT stored", row);
        return stored;
    }

private:
    // Appends the row, after the header if the file is new
    bool write(const char* row) {
        if (!SD.begin(kSdCsPin)) {
            Serial.println("   SD card not found");
            return false;
        }
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
};
