/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/FlashStorage.h
 *
 * Description:
 * Storage adapter for the flash memory of the ESP32: appends each row to
 * the CSV file /measurements_v1.csv, appends the log of each wake-up to
 * /log.txt, and gives back the rows and log lines after their upload
 * cursors (/upload.idx, /log.idx). When a file is full, it becomes the
 * previous file and a new one starts, so that the memory never fills up.
 *
 * Wiring: none (the flash memory is part of the ESP32 module).
 * Dependencies: ESP32 Arduino core (LittleFS, FS), lib/core (CSV format,
 * rotation rule), FlashVolume.h.
 */

#pragma once

#include <Arduino.h>
#include <LittleFS.h>

#include "Console.h"
#include "CsvFormat.h"
#include "FlashVolume.h"
#include "IStorage.h"
#include "Rules.h"

/**
 * @brief Storage adapter for the flash memory.
 *
 * If the file system cannot be mounted or written, append() reports it
 * and returns false: the row is lost, but the station keeps its schedule.
 */
class FlashStorage : public IStorage {
public:
    /**
     * @brief Creates the storage on the flash file system.
     *
     * @param[in,out] volume The file system, shared with the maintenance
     *                mode.
     */
    explicit FlashStorage(FlashVolume& volume) : volume_(volume) {}

    bool append(const Record& record) override {
        char row[kCsvRowSize];
        if (!formatCsvRow(record, row, sizeof(row))) {
            console.println("   row too long for the buffer");
            return false;
        }
        // The timestamp starts the row: kept to date the log entry
        memcpy(wakeTime_, row, sizeof(wakeTime_) - 1);
        bool stored = volume_.mount() && write(row);
        console.printf("   %s: %s\n", stored ? "stored" : "NOT stored", row);
        return stored;
    }

    size_t readUnsent(DataKind kind, char* buffer, size_t size) override {
        return volume_.mount() ? read(kind, buffer, size) : 0;
    }

    bool markSent(DataKind kind, size_t length) override {
        return volume_.mount() &&
               saveCursor(cursorFile(kind), unsentStart_ + length);
    }

    void close() override {
        // The last line of the log of this wake-up
        console.printf("   awake for %lu ms\n",
                       static_cast<unsigned long>(millis()));
        // Only if the file system was usable during the wake-up
        if (volume_.isMounted()) {
            writeLog();
        }
        volume_.unmount();
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
        startNewFileIfFull();
        bool newFile = !LittleFS.exists(kCsvFileName);
        File file = LittleFS.open(kCsvFileName, FILE_APPEND);
        if (!file) {
            console.println("   cannot open the CSV file");
            return false;
        }
        if (newFile) {
            file.println(kCsvHeader);
        }
        // println() returns the number of bytes written: 0 means failure,
        // for example when the flash memory is full
        bool written = file.println(row) > 0;
        file.close();
        return written;
    }

    // When the CSV file is full and the server has all its rows, it
    // becomes the previous file, and the next row starts a new file. The
    // former previous file is deleted: the server has its rows too.
    void startNewFileIfFull() {
        uint32_t size = volume_.fileSize(kCsvFileName);
        uint32_t cursor = volume_.loadCursor(kCursorFileName);
        if (!isRotationDue(size, cursor, volume_.maxFileSize(false))) {
            return;
        }
        LittleFS.remove(kOldCsvFileName);
        LittleFS.rename(kCsvFileName, kOldCsvFileName);
        // The new file is read from its start
        LittleFS.remove(kCursorFileName);
        console.println("   measurements file full and sent: new file");
    }

    // Appends what the console kept during this wake-up to the log file
    void writeLog() {
        // Rotation: past its maximum size, the log becomes the old log,
        // and the previous old log is deleted. The log is a help, not
        // data: its unsent lines are no longer uploaded, but stay in the
        // old log.
        if (volume_.fileSize(kLogFileName) > volume_.maxFileSize(true)) {
            LittleFS.remove(kOldLogFileName);
            LittleFS.rename(kLogFileName, kOldLogFileName);
            LittleFS.remove(kLogCursorFileName);
        }
        File file = LittleFS.open(kLogFileName, FILE_APPEND);
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
        if (!LittleFS.exists(dataFile(kind))) {
            return 0;  // no file yet: nothing to send
        }
        File file = LittleFS.open(dataFile(kind), FILE_READ);
        if (!file) {
            return 0;
        }
        uint32_t cursor = volume_.loadCursor(cursorFile(kind));
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
    // FlashVolume::loadCursor())
    bool saveCursor(const char* fileName, uint32_t cursor) {
        // FILE_WRITE replaces the previous content
        File file = LittleFS.open(fileName, FILE_WRITE);
        if (!file) {
            console.println("   cannot save the upload cursor");
            return false;
        }
        bool saved = file.print(cursor) > 0;
        file.close();
        return saved;
    }

    FlashVolume& volume_;
    uint32_t unsentStart_ = 0;  // where the lines of the last read start
    char wakeTime_[21] = "unknown time";  // timestamp of the last row
};
