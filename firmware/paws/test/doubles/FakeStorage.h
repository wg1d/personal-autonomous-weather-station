/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/FakeStorage.h
 *
 * Description:
 * Fake storage: keeps the rows in RAM instead of the SD card, as records
 * and as CSV text with its upload cursor, and adds a "store" event to the
 * shared log.
 *
 * Dependencies: lib/ports, lib/core (CSV format), EventLog.h.
 */

#pragma once

#include <cstring>
#include <string>
#include <vector>

#include "CsvFormat.h"
#include "EventLog.h"
#include "IStorage.h"

/**
 * @brief Fake storage: keeps the rows in RAM, logs "store".
 */
class FakeStorage : public IStorage {
public:
    /**
     * @brief Creates an empty storage.
     *
     * @param[in,out] log The shared log, where "store" is added.
     */
    explicit FakeStorage(EventLog& log) : log_(log) {}

    std::vector<Record> rows;  ///< The rows stored, oldest first
    std::string csv;           ///< The same rows, as the CSV file content
    size_t cursor = 0;         ///< Position of the first unsent row in csv
    bool working = true;       ///< false simulates a missing or full card

    bool append(const Record& record) override {
        log_.add("store");
        if (!working) {
            return false;
        }
        rows.push_back(record);
        char row[kCsvRowSize];
        formatCsvRow(record, row, sizeof(row));
        csv += row;
        csv += "\r\n";
        return true;
    }

    size_t readUnsent(char* buffer, size_t size) override {
        // Complete rows only: cut after the last line break that fits
        size_t length = csv.size() - cursor;
        if (length > size) {
            length = csv.rfind('\n', cursor + size - 1) + 1 - cursor;
        }
        memcpy(buffer, csv.data() + cursor, length);
        return length;
    }

    bool markSent(size_t length) override {
        cursor += length;
        return true;
    }

private:
    EventLog& log_;
};
