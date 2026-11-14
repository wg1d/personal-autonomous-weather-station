/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/CsvFormat.h
 *
 * Description:
 * The CSV format of the measurement file, version 2 (see the Data and
 * Upload chapter of the Phase 4 design): the columns of version 1, then
 * the voltage and the current of the battery. A file never mixes two
 * formats: the rows of version 2 go to a new file.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstddef>

#include "Record.h"

/// Name of the measurement file in the storage
const char kCsvFileName[] = "/measurements_v2.csv";

/// Previous measurement file, kept when the current one is full and sent
const char kOldCsvFileName[] = "/measurements_v2_old.csv";

/// The files of the format version 1, written by the firmware before the
/// battery monitor. Their rows were sent; they are only removed with the
/// measurements, from the maintenance page
const char kV1CsvFileName[] = "/measurements_v1.csv";
const char kV1OldCsvFileName[] = "/measurements_v1_old.csv";

/// First line of the file: the name and unit of each column
const char kCsvHeader[] =
    "timestamp,time_valid,temperature_c,humidity_pct,pressure_hpa,"
    "battery_v,battery_ma";

/// Size of a buffer large enough for any row, end of string included
const size_t kCsvRowSize = 80;

/**
 * @brief Writes a record as one CSV row, without the end of line.
 *
 * Example: `2026-10-01T14:15:00Z,1,18.42,62.10,1013.20,4.05,-1.25`. A
 * missing value
 * (NaN) gives an empty field.
 *
 * @param[in] record The record to write.
 * @param[out] buffer Where the row is written, as a C string.
 * @param[in] size The size of the buffer, in bytes.
 * @return true if the row fits in the buffer; false otherwise.
 */
bool formatCsvRow(const Record& record, char* buffer, size_t size);
