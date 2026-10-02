/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/CsvFormat.cpp
 *
 * Description:
 * Implementation of the CSV row format (see CsvFormat.h).
 *
 * Dependencies: none (standard C++ only).
 */

#include "CsvFormat.h"

#include <cmath>
#include <cstdio>
#include <ctime>

// Writes a value with two decimals, or nothing if it is missing, so that
// its CSV field stays empty
static void formatValue(float value, char* text, size_t size) {
    if (std::isnan(value)) {
        text[0] = '\0';
    } else {
        snprintf(text, size, "%.2f", value);
    }
}

bool formatCsvRow(const Record& record, char* buffer, size_t size) {
    // ISO 8601 in UTC, with the explicit Z suffix: 2026-10-01T14:15:00Z
    time_t t = record.timestamp;
    char timestamp[21];
    std::strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ",
                  std::gmtime(&t));

    // Large enough for any value a weather sensor can return
    char temperature[16];
    char humidity[16];
    char pressure[16];
    formatValue(record.values.temperatureC, temperature, sizeof(temperature));
    formatValue(record.values.humidityPct, humidity, sizeof(humidity));
    formatValue(record.values.pressureHpa, pressure, sizeof(pressure));

    // snprintf never writes past the end of the buffer; it returns the
    // length the full row needs, which tells us whether it was cut
    int length = snprintf(buffer, size, "%s,%d,%s,%s,%s", timestamp,
                          record.timeValid ? 1 : 0, temperature, humidity,
                          pressure);
    return length >= 0 && static_cast<size_t>(length) < size;
}
