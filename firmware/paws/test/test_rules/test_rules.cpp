/*
 * Project: Personal Autonomous Weather Station
 * File: test/test_rules/test_rules.cpp
 *
 * Description:
 * Unit tests of the pure decision rules (lib/core/Rules.h). Each test
 * checks one function with chosen inputs.
 *
 * Dependencies: lib/core, Unity.
 */

#include <unity.h>

#include "Rules.h"

// 2026-10-01T00:00:00Z
const uint32_t kDayStart = 1790812800;

// Unix time of hh:mm:ss on 2026-10-01, UTC
uint32_t at(uint32_t h, uint32_t m, uint32_t s) {
    return kDayStart + h * 3600 + m * 60 + s;
}

const Config config;  // default values of the design chapter

void setUp() {}
void tearDown() {}

// --- nextAlarm (F1) ---

void test_next_alarm_is_next_grid_slot() {
    TEST_ASSERT_EQUAL_UINT32(at(14, 15, 0), nextAlarm(at(14, 7, 23), config));
}

void test_next_alarm_is_strictly_after_now() {
    TEST_ASSERT_EQUAL_UINT32(at(14, 30, 0), nextAlarm(at(14, 15, 0), config));
}

void test_next_alarm_crosses_midnight() {
    TEST_ASSERT_EQUAL_UINT32(kDayStart + 24 * 3600,
                             nextAlarm(at(23, 59, 59), config));
}

// --- isUploadNeeded (F3, F6) ---

void test_upload_needed_on_full_hour_slot() {
    // Woken 3 s after the 14:00 alarm
    TEST_ASSERT_TRUE(isUploadNeeded(at(14, 0, 3), true, config));
}

void test_upload_needed_after_safety_timer_wake_up() {
    // Woken by the safety timer, 60 s after the missed 14:00 alarm
    TEST_ASSERT_TRUE(isUploadNeeded(at(14, 1, 0), true, config));
}

void test_no_upload_on_quarter_slots() {
    TEST_ASSERT_FALSE(isUploadNeeded(at(14, 15, 3), true, config));
    TEST_ASSERT_FALSE(isUploadNeeded(at(14, 30, 3), true, config));
    TEST_ASSERT_FALSE(isUploadNeeded(at(14, 45, 3), true, config));
}

void test_upload_needed_when_clock_invalid() {
    TEST_ASSERT_TRUE(isUploadNeeded(at(14, 15, 3), false, config));
}

// --- isSyncNeeded (F4) ---

void test_sync_needed_when_clock_invalid() {
    TEST_ASSERT_TRUE(isSyncNeeded(at(14, 0, 3), false, at(13, 0, 0),
                                  config));
}

void test_sync_needed_when_never_synced() {
    TEST_ASSERT_TRUE(isSyncNeeded(at(14, 0, 3), true, 0, config));
}

void test_no_sync_when_last_sync_is_recent() {
    TEST_ASSERT_FALSE(isSyncNeeded(at(23, 0, 3), true, at(0, 0, 3),
                                   config));
}

void test_sync_needed_after_one_day() {
    TEST_ASSERT_TRUE(isSyncNeeded(at(0, 0, 3) + 24 * 3600, true,
                                  at(0, 0, 3), config));
}

// --- safetyTimerSeconds (N2) ---

void test_safety_timer_fires_after_the_alarm() {
    // Alarm in 897 s, plus the 60 s margin
    TEST_ASSERT_EQUAL_UINT32(957, safetyTimerSeconds(at(14, 0, 3),
                                                     at(14, 15, 0), true,
                                                     config));
}

void test_safety_timer_is_one_interval_without_alarm() {
    TEST_ASSERT_EQUAL_UINT32(900, safetyTimerSeconds(at(14, 0, 3),
                                                     at(14, 15, 0), false,
                                                     config));
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_next_alarm_is_next_grid_slot);
    RUN_TEST(test_next_alarm_is_strictly_after_now);
    RUN_TEST(test_next_alarm_crosses_midnight);
    RUN_TEST(test_upload_needed_on_full_hour_slot);
    RUN_TEST(test_upload_needed_after_safety_timer_wake_up);
    RUN_TEST(test_no_upload_on_quarter_slots);
    RUN_TEST(test_upload_needed_when_clock_invalid);
    RUN_TEST(test_sync_needed_when_clock_invalid);
    RUN_TEST(test_sync_needed_when_never_synced);
    RUN_TEST(test_no_sync_when_last_sync_is_recent);
    RUN_TEST(test_sync_needed_after_one_day);
    RUN_TEST(test_safety_timer_fires_after_the_alarm);
    RUN_TEST(test_safety_timer_is_one_interval_without_alarm);
    return UNITY_END();
}
