/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/FakeStorage.h
 *
 * Description:
 * Fake storage: keeps the rows in RAM instead of the SD card, as records
 * and as CSV text with its upload cursor, keeps a log text with its own
 * cursor, and adds the "store" and "close" events to the shared log.
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
 * @brief Fake storage: keeps the rows in RAM, logs "store" and "close".
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
    std::string log;           ///< The log lines, set by the test
    size_t logCursor = 0;      ///< Position of the first unsent log line
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

    size_t readUnsent(DataKind kind, char* buffer, size_t size) override {
        const std::string& text = kind == DataKind::Log ? log : csv;
        size_t from = kind == DataKind::Log ? logCursor : cursor;
        // Complete lines only: cut after the last line break that fits
        size_t length = text.size() - from;
        if (length > size) {
            length = text.rfind('\n', from + size - 1) + 1 - from;
        }
        memcpy(buffer, text.data() + from, length);
        return length;
    }

    bool markSent(DataKind kind, size_t length) override {
        if (kind == DataKind::Log) {
            logCursor += length;
        } else {
            cursor += length;
        }
        return true;
    }

    void close() override { log_.add("close"); }

private:
    EventLog& log_;
};
