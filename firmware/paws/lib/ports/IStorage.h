/*
 * Project: Personal Autonomous Weather Station
 * File: lib/ports/IStorage.h
 *
 * Description:
 * What the core needs from the storage. Step A1 only appends rows;
 * reading the rows after the upload cursor comes with the upload (A4).
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

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
};
