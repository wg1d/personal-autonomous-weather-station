/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/CsvFormat.h
 *
 * Description:
 * The CSV format of the measurement file, version 1 (see the Data and
 * Upload chapter of the Phase 4 design).
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstddef>

#include "Record.h"

/// Name of the measurement file on the SD card
const char kCsvFileName[] = "/measurements_v1.csv";

/// First line of the file: the name and unit of each column
const char kCsvHeader[] =
    "timestamp,time_valid,temperature_c,humidity_pct,pressure_hpa";

/// Size of a buffer large enough for any row, end of string included
const size_t kCsvRowSize = 80;

/**
 * @brief Writes a record as one CSV row, without the end of line.
 *
 * Example: `2026-10-01T14:15:00Z,1,18.42,62.10,1013.20`. A missing value
 * (NaN) gives an empty field.
 *
 * @param[in] record The record to write.
 * @param[out] buffer Where the row is written, as a C string.
 * @param[in] size The size of the buffer, in bytes.
 * @return true if the row fits in the buffer; false otherwise.
 */
bool formatCsvRow(const Record& record, char* buffer, size_t size);
