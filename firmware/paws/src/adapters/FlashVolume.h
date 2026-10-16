/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/FlashVolume.h
 *
 * Description:
 * The file system in the flash memory of the ESP32, shared by the
 * storage adapter and the maintenance mode: its files, and the size of
 * each one. It is mounted at its first use in a wake-up, and stays
 * mounted until the end of the wake-up.
 *
 * Wiring: none (the flash memory is part of the ESP32 module).
 * Dependencies: ESP32 Arduino core (LittleFS, FS).
 */

#pragma once

#include <Arduino.h>
#include <LittleFS.h>

#include "Console.h"

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
 * @brief The file system in the flash memory: mounting and sizes.
 *
 * One object is created by main.cpp and given to the adapters that use
 * the files, so that they share its state.
 */
class FlashVolume {
public:
    /**
     * @brief Mounts the file system, if not done yet.
     *
     * The very first time, the flash memory holds no file system yet:
     * LittleFS formats it (true), then mounts it.
     *
     * @return true if the files can be used.
     */
    bool mount() {
        if (mounted_) {
            return true;
        }
        if (!LittleFS.begin(true)) {
            console.println("   flash file system not mounted");
            return false;
        }
        mounted_ = true;
        return true;
    }

    /**
     * @brief Unmounts the file system, before the deep sleep.
     */
    void unmount() {
        if (mounted_) {
            LittleFS.end();
            mounted_ = false;
        }
    }

    /**
     * @brief Tells whether the file system is mounted.
     *
     * @return true between a successful mount() and unmount().
     */
    bool isMounted() const { return mounted_; }

    /**
     * @brief Size of a file, which must be mounted.
     *
     * @param[in] fileName The file, such as kLogFileName.
     * @return Its size in bytes; 0 if it does not exist.
     */
    uint32_t fileSize(const char* fileName) {
        // Check first: opening a missing file prints an error of the
        // library, although it is a normal case here
        if (!LittleFS.exists(fileName)) {
            return 0;
        }
        File file = LittleFS.open(fileName, FILE_READ);
        uint32_t size = file.size();
        file.close();
        return size;
    }

    /**
     * @brief Maximum size of each data file, before it starts again.
     *
     * The flash memory holds two files of measurements (the current and
     * the previous one) and two log files. A quarter of the space for each
     * file of measurements and an eighth for each log file use three
     * quarters of it, and leave room for the cursors and for a file that
     * keeps growing while the server cannot be reached.
     *
     * @param[in] isLog true for the log, false for the measurements.
     * @return The size in bytes.
     */
    uint32_t maxFileSize(bool isLog) {
        uint32_t total = LittleFS.totalBytes();
        return isLog ? total / 8 : total / 4;
    }

    /**
     * @brief Reads an upload cursor; the file system must be mounted.
     *
     * A missing file means that nothing was sent yet: everything is sent
     * again, and the server ignores the rows it already has.
     *
     * @param[in] fileName The cursor file, such as kCursorFileName.
     * @return The cursor, stored as text such as "1234"; 0 if there is
     *         none.
     */
    uint32_t loadCursor(const char* fileName) {
        if (!LittleFS.exists(fileName)) {
            return 0;
        }
        File file = LittleFS.open(fileName, FILE_READ);
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
