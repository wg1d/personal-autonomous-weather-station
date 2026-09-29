/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/FakeStorage.h
 *
 * Description:
 * Fake storage: keeps the rows in RAM instead of the SD card, and adds
 * a "store" event to the shared log.
 *
 * Dependencies: lib/ports, EventLog.h.
 */

#pragma once

#include <vector>

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
    bool working = true;       ///< false simulates a missing or full card

    bool append(const Record& record) override {
        log_.add("store");
        if (!working) {
            return false;
        }
        rows.push_back(record);
        return true;
    }

private:
    EventLog& log_;
};
