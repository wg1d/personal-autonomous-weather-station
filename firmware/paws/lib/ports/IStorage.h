/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/IStorage.h
 *
 * Description:
 * What the core needs from the storage: append the rows, and give back
 * the rows that the server has not acknowledged yet, with the upload
 * cursor that remembers where they start.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstddef>

#include "Record.h"

/**
 * @brief The storage that keeps every row: the source of truth.
 *
 * Implemented by the SD card adapter on the board, and by a fake
 * storage in RAM in the tests.
 */
class IStorage {
public:
    virtual ~IStorage() = default;

    /**
     * @brief Appends one row at the end of the storage.
     *
     * Called once per wake-up, before any network activity (F2).
     *
     * @param[in] record The row to store.
     * @return true if the row is stored; false if it could not be written
     *         (card missing or full). The schedule continues anyway.
     */
    virtual bool append(const Record& record) = 0;

    /**
     * @brief Reads the rows that the server has not acknowledged yet.
     *
     * Starts at the upload cursor, and stops before a row that would not
     * fit: the buffer only holds complete rows, each one ending with a
     * line break. The cursor does not move.
     *
     * @param[out] buffer Where the rows are written (not a C string: no
     *             end-of-string character is added).
     * @param[in] size The size of the buffer, in bytes.
     * @return The number of bytes written; 0 if every row was sent, or if
     *         the storage cannot be read.
     */
    virtual size_t readUnsent(char* buffer, size_t size) = 0;

    /**
     * @brief Moves the upload cursor after rows the server acknowledged.
     *
     * Called only after the server confirmed the reception, so that a
     * row is never skipped (N1). The cursor survives power losses.
     *
     * @param[in] length The number of bytes acknowledged, as returned by
     *            the last readUnsent().
     * @return true if the new cursor was saved.
     */
    virtual bool markSent(size_t length) = 0;
};
