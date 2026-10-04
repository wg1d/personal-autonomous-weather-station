/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/Console.h
 *
 * Description:
 * The console of the station: what the adapters print goes to the serial
 * port, as with Serial, and is also kept in memory until the end of the
 * wake-up, when the storage appends it to the log file of the SD card.
 *
 * Wiring: none (USB serial only).
 * Dependencies: ESP32 Arduino core.
 */

#pragma once

#include <Arduino.h>

/// Size of the copy kept in memory: a wake-up prints a few hundred bytes
const size_t kConsoleBufferSize = 4096;

/**
 * @brief Prints to the serial port and keeps a copy for the log.
 *
 * It inherits from Print, like Serial: print(), println() and printf()
 * work the same way. Only write() is redefined, since all of them end up
 * calling it for each character.
 */
class Console : public Print {
public:
    /**
     * @brief Prints one character, and keeps it if there is room left.
     *
     * @param[in] c The character.
     * @return 1: the character is always printed on the serial port.
     */
    size_t write(uint8_t c) override {
        Serial.write(c);
        if (length_ < sizeof(buffer_)) {
            buffer_[length_++] = static_cast<char>(c);
        } else {
            truncated_ = true;
        }
        return 1;
    }

    /**
     * @brief The characters kept since the start of the wake-up.
     *
     * @return The first character (not a C string: see length()).
     */
    const char* text() const { return buffer_; }

    /**
     * @brief The number of characters kept.
     *
     * @return The number of characters in text().
     */
    size_t length() const { return length_; }

    /**
     * @brief Tells whether characters were lost.
     *
     * @return true if the buffer was full and characters were not kept.
     */
    bool truncated() const { return truncated_; }

private:
    char buffer_[kConsoleBufferSize];
    size_t length_ = 0;
    bool truncated_ = false;
};

/// The console used by every adapter, created in main.cpp
extern Console console;
