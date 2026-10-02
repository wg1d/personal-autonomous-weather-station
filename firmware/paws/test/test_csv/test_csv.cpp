/*
 * Project: Personal Autonomous Weather Station
 * File: test/test_csv/test_csv.cpp
 *
 * Description:
 * Unit tests of the CSV row format (lib/core/CsvFormat.h), against the
 * examples of the Data and Upload chapter of the Phase 4 design.
 *
 * Dependencies: lib/core, Unity.
 */

#include <unity.h>

#include "CsvFormat.h"

// 2026-10-01T14:15:00Z
const uint32_t kQuarterPast = 1790864100;

void setUp() {}
void tearDown() {}

Record makeRecord() {
    Record record;
    record.timestamp = kQuarterPast;
    record.timeValid = true;
    record.values.temperatureC = 18.42f;
    record.values.humidityPct = 62.10f;
    record.values.pressureHpa = 1013.20f;
    return record;
}

void test_complete_row() {
    char row[kCsvRowSize];
    TEST_ASSERT_TRUE(formatCsvRow(makeRecord(), row, sizeof(row)));
    TEST_ASSERT_EQUAL_STRING("2026-10-01T14:15:00Z,1,18.42,62.10,1013.20",
                             row);
}

void test_missing_value_gives_empty_field() {
    Record record = makeRecord();
    record.values.humidityPct = NAN;
    char row[kCsvRowSize];
    TEST_ASSERT_TRUE(formatCsvRow(record, row, sizeof(row)));
    TEST_ASSERT_EQUAL_STRING("2026-10-01T14:15:00Z,1,18.42,,1013.20", row);
}

void test_sensor_missing_gives_three_empty_fields() {
    Record record;
    record.timestamp = kQuarterPast;
    char row[kCsvRowSize];
    TEST_ASSERT_TRUE(formatCsvRow(record, row, sizeof(row)));
    TEST_ASSERT_EQUAL_STRING("2026-10-01T14:15:00Z,0,,,", row);
}

void test_unreliable_time_is_flagged() {
    Record record = makeRecord();
    record.timeValid = false;
    char row[kCsvRowSize];
    TEST_ASSERT_TRUE(formatCsvRow(record, row, sizeof(row)));
    TEST_ASSERT_EQUAL_STRING("2026-10-01T14:15:00Z,0,18.42,62.10,1013.20",
                             row);
}

void test_negative_temperature() {
    Record record = makeRecord();
    record.values.temperatureC = -3.5f;
    char row[kCsvRowSize];
    TEST_ASSERT_TRUE(formatCsvRow(record, row, sizeof(row)));
    TEST_ASSERT_EQUAL_STRING("2026-10-01T14:15:00Z,1,-3.50,62.10,1013.20",
                             row);
}

void test_buffer_too_small_is_refused() {
    char row[20];
    TEST_ASSERT_FALSE(formatCsvRow(makeRecord(), row, sizeof(row)));
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_complete_row);
    RUN_TEST(test_missing_value_gives_empty_field);
    RUN_TEST(test_sensor_missing_gives_three_empty_fields);
    RUN_TEST(test_unreliable_time_is_flagged);
    RUN_TEST(test_negative_temperature);
    RUN_TEST(test_buffer_too_small_is_refused);
    return UNITY_END();
}
