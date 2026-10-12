/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/SdStorage.h
 *
 * Description:
 * Storage adapter for the SD card: appends each row to the CSV file
 * /measurements_v1.csv, appends the log of each wake-up to /log.txt, and
 * gives back the rows and log lines after their upload cursors
 * (/upload.idx, /log.idx). The card module is powered only during the
 * wake-up.
 *
 * Wiring:
 * - SD card: 5V -> VCC, GND -> GND, Pin 19 -> MISO, Pin 23 -> MOSI,
 *            Pin 18 -> SCLK, Pin 5 -> CS,
 *            Pin 13 -> OFF (10k pull-down resistor to GND)
 * Dependencies: ESP32 Arduino core (SD, FS), lib/core (CSV format),
 * SdCard.h.
 */

#pragma once

#include <Arduino.h>
#include <SD.h>

#include "Console.h"
#include "CsvFormat.h"
#include "IStorage.h"
#include "SdCard.h"

/// Maximum size of the log file, about a month of wake-ups with the
/// periods of the design (about 300 bytes per wake-up)
const size_t kLogMaxSize = 1024 * 1024;

/**
 * @brief Storage adapter for the SD card.
 *
 * If the card is missing or cannot be written, append() reports it and
 * returns false: the row is lost, but the station keeps its schedule.
 */
class SdStorage : public IStorage {
public:
    /**
     * @brief Creates the storage on an SD card.
     *
     * @param[in,out] card The card module, shared with the maintenance
     *                mode.
     */
    explicit SdStorage(SdCard& card) : card_(card) {}

    bool append(const Record& record) override {
        char row[kCsvRowSize];
        if (!formatCsvRow(record, row, sizeof(row))) {
            console.println("   row too long for the buffer");
            return false;
        }
        // The timestamp starts the row: kept to date the log entry
        memcpy(wakeTime_, row, sizeof(wakeTime_) - 1);
        bool stored = card_.mount() && write(row);
        console.printf("   %s: %s\n", stored ? "stored" : "NOT stored", row);
        return stored;
    }

    size_t readUnsent(DataKind kind, char* buffer, size_t size) override {
        return card_.mount() ? read(kind, buffer, size) : 0;
    }

    bool markSent(DataKind kind, size_t length) override {
        return card_.mount() &&
               saveCursor(cursorFile(kind), unsentStart_ + length);
    }

    void close() override {
        // The last line of the log of this wake-up
        console.printf("   awake for %lu ms\n",
                       static_cast<unsigned long>(millis()));
        // Only if the card was usable during the wake-up: trying to mount
        // a missing card again would only make the wake-up longer
        if (card_.isMounted()) {
            writeLog();
        }
        card_.unmount();
    }

private:
    static const char* dataFile(DataKind kind) {
        return kind == DataKind::Log ? kLogFileName : kCsvFileName;
    }

    static const char* cursorFile(DataKind kind) {
        return kind == DataKind::Log ? kLogCursorFileName : kCursorFileName;
    }

    // Appends the row, after the header if the file is new
    bool write(const char* row) {
        bool newFile = !SD.exists(kCsvFileName);
        File file = SD.open(kCsvFileName, FILE_APPEND);
        if (!file) {
            console.println("   cannot open the CSV file");
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

    // Appends what the console kept during this wake-up to the log file
    void writeLog() {
        // Rotation: past its maximum size, the log becomes the old log,
        // and the previous old log is deleted. Its unsent lines are no
        // longer uploaded, but stay on the card.
        if (SD.exists(kLogFileName)) {
            File current = SD.open(kLogFileName, FILE_READ);
            size_t size = current.size();
            current.close();
            if (size > kLogMaxSize) {
                SD.remove(kOldLogFileName);
                SD.rename(kLogFileName, kOldLogFileName);
                SD.remove(kLogCursorFileName);
            }
        }
        File file = SD.open(kLogFileName, FILE_APPEND);
        if (!file) {
            return;  // the log is a help, not data: nothing more to do
        }
        // A blank line, then the date of the wake-up, before its lines
        file.printf("\n=== %s ===\n", wakeTime_);
        // The console starts with a line break, which separates the first
        // line from the boot messages on the serial port: not needed here
        const char* text = console.text();
        size_t length = console.length();
        if (length > 0 && text[0] == '\n') {
            ++text;
            --length;
        }
        file.write(reinterpret_cast<const uint8_t*>(text), length);
        if (console.truncated()) {
            file.println("   (log of this wake-up truncated)");
        }
        file.close();
    }

    // Reads complete lines from the cursor, as many as fit in the buffer
    size_t read(DataKind kind, char* buffer, size_t size) {
        // Check first: opening a missing file prints an error of the
        // SD library, although it is a normal case here
        if (!SD.exists(dataFile(kind))) {
            return 0;  // no file yet: nothing to send
        }
        File file = SD.open(dataFile(kind), FILE_READ);
        if (!file) {
            return 0;
        }
        uint32_t cursor = card_.loadCursor(cursorFile(kind));
        if (cursor == 0 && kind == DataKind::Measurements) {
            // Start of the CSV file: skip the header line, which the core
            // adds to each request itself
            while (file.available() && file.read() != '\n') {
            }
            cursor = file.position();
        }
        file.seek(cursor);
        size_t length = file.read(reinterpret_cast<uint8_t*>(buffer), size);
        file.close();

        // Keep complete lines only: cut after the last line break
        while (length > 0 && buffer[length - 1] != '\n') {
            --length;
        }
        // markSent() moves the cursor from here
        unsentStart_ = cursor;
        return length;
    }

    // The cursor is stored as text, for example "1234" (see
    // SdCard::loadCursor())
    bool saveCursor(const char* fileName, uint32_t cursor) {
        // FILE_WRITE replaces the previous content
        File file = SD.open(fileName, FILE_WRITE);
        if (!file) {
            console.println("   cannot save the upload cursor");
            return false;
        }
        bool saved = file.print(cursor) > 0;
        file.close();
        return saved;
    }

    SdCard& card_;
    uint32_t unsentStart_ = 0;  // where the lines of the last read start
    char wakeTime_[21] = "unknown time";  // timestamp of the last row
};
