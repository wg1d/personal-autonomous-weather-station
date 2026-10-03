/*
 * Project: Personal Autonomous Weather Station
 * File: test/test_scenarios/test_scenarios.cpp
 *
 * Description:
 * Scenario tests: the whole state machine runs with test doubles, and
 * each test checks an acceptance criterion of the verification matrix.
 *
 * Dependencies: lib/core, test/doubles, Unity.
 */

#include <unity.h>

#include <cmath>

#include "Station.h"

using S = State;

void setUp() {}
void tearDown() {}

// --- Paths through the state machine ---

void test_quarter_hour_wake_up_only_measures() {
    Station station;
    station.clock.time = at(14, 15, kWakeDelayS);
    station.wake();

    TEST_ASSERT_TRUE(station.visited(
        {S::Boot, S::Measure, S::Store, S::Schedule, S::Sleep}));
    TEST_ASSERT_EQUAL(0, station.log.count("connect"));
}

void test_full_hour_wake_up_uploads() {
    Station station;
    station.wake();

    TEST_ASSERT_TRUE(station.visited(
        {S::Boot, S::Measure, S::Store, S::Upload, S::Schedule, S::Sleep}));
    TEST_ASSERT_EQUAL(1, station.log.count("connect"));
    TEST_ASSERT_EQUAL(1, station.log.count("disconnect"));
}

void test_button_wake_up_runs_maintenance_then_measures() {
    Station station;
    station.power.cause = WakeCause::Button;
    station.clock.time = at(14, 13, 0);
    station.wake();

    TEST_ASSERT_TRUE(station.visited(
        {S::Boot, S::Maintenance, S::Measure, S::Store, S::Schedule,
         S::Sleep}));
    TEST_ASSERT_EQUAL(1, station.maintenance.runCount);
    // The session ended at 14:16: the row has that time, and the next
    // alarm is computed from it, not from the time at boot
    TEST_ASSERT_EQUAL_UINT32(at(14, 16, 0), station.storage.rows[0].timestamp);
    TEST_ASSERT_EQUAL_UINT32(at(14, 30, 0), station.clock.lastAlarm);
}

// --- F1 · Periodic measurement ---

void test_f1_alarm_on_grid_and_in_the_future() {
    Station station;
    station.clock.time = at(14, 7, 23);  // e.g. after a power-on
    station.power.cause = WakeCause::PowerOn;
    station.wake();

    TEST_ASSERT_EQUAL_UINT32(at(14, 15, 0), station.clock.lastAlarm);
    TEST_ASSERT_TRUE(station.power.lastPlan.rtcAlarm);
}

// --- F2 · Store first ---

void test_f2_row_stored_before_any_network_call() {
    Station station;
    station.wake();

    int store = station.log.indexOf("store");
    int connect = station.log.indexOf("connect");
    TEST_ASSERT_NOT_EQUAL(-1, store);
    TEST_ASSERT_NOT_EQUAL(-1, connect);
    TEST_ASSERT_LESS_THAN(connect, store);
}

// --- F6 · Flag unreliable time ---

void test_f6_rows_flagged_until_ntp_succeeds() {
    Station station;
    station.clock.valid = false;  // RTC lost power
    station.network.ntpAvailable = false;
    station.clock.time = at(14, 15, kWakeDelayS);
    station.wake();

    // Clock invalid: upload attempted at every wake-up, to reach NTP
    TEST_ASSERT_TRUE(station.visited(
        {S::Boot, S::Measure, S::Store, S::Upload, S::TimeSync,
         S::Schedule, S::Sleep}));
    TEST_ASSERT_FALSE(station.storage.rows[0].timeValid);

    // NTP comes back: the clock is corrected during this wake-up...
    station.network.ntpAvailable = true;
    station.wakeAtNextAlarm();
    TEST_ASSERT_FALSE(station.storage.rows[1].timeValid);
    TEST_ASSERT_TRUE(station.clock.valid);

    // ...so the rows of the following wake-ups are valid
    station.wakeAtNextAlarm();
    TEST_ASSERT_TRUE(station.storage.rows[2].timeValid);
}

// --- N1 · No data loss ---

void test_n1_wifi_down_at_full_hour() {
    Station station;
    station.network.wifiAvailable = false;
    station.wake();

    TEST_ASSERT_EQUAL(1, station.storage.rows.size());
    TEST_ASSERT_EQUAL_UINT32(at(14, 15, 0), station.clock.lastAlarm);
    TEST_ASSERT_EQUAL(1, station.power.sleepCount);
}

void test_n1_ntp_down_keeps_schedule() {
    Station station;
    station.clock.lastSet = 0;  // sync needed
    station.network.ntpAvailable = false;
    station.wake();

    TEST_ASSERT_EQUAL(1, station.storage.rows.size());
    TEST_ASSERT_EQUAL(0, station.clock.setTimeCount);
    TEST_ASSERT_EQUAL_UINT32(0, station.clock.lastSet);
    TEST_ASSERT_EQUAL(1, station.log.count("disconnect"));
    TEST_ASSERT_EQUAL(1, station.power.sleepCount);
}

void test_n1_sensor_missing_row_still_stored() {
    Station station;
    station.sensor.responding = false;
    station.wake();

    TEST_ASSERT_EQUAL(1, station.storage.rows.size());
    TEST_ASSERT_TRUE(std::isnan(station.storage.rows[0].values.temperatureC));
    TEST_ASSERT_EQUAL(1, station.power.sleepCount);
}

void test_n1_storage_failure_keeps_schedule() {
    Station station;
    station.storage.working = false;
    station.wake();

    TEST_ASSERT_EQUAL_UINT32(at(14, 15, 0), station.clock.lastAlarm);
    TEST_ASSERT_EQUAL(1, station.power.sleepCount);
}

// --- N2 · Always wake up again ---

void test_n2_rtc_alarm_and_safety_timer_armed() {
    Station station;
    station.wake();

    const SleepPlan& plan = station.power.lastPlan;
    TEST_ASSERT_TRUE(plan.rtcAlarm);
    TEST_ASSERT_TRUE(plan.button);
    // 14:00:03 -> alarm at 14:15:00 (897 s), timer 60 s later
    TEST_ASSERT_EQUAL_UINT32(897 + 60, plan.timerSeconds);
}

void test_n2_rtc_failure_safety_timer_only() {
    Station station;
    station.clock.alarmWorks = false;
    station.wake();

    const SleepPlan& plan = station.power.lastPlan;
    TEST_ASSERT_EQUAL(1, station.power.sleepCount);
    TEST_ASSERT_FALSE(plan.rtcAlarm);
    TEST_ASSERT_EQUAL_UINT32(station.config.measurementIntervalS,
                             plan.timerSeconds);
}

// --- F3 · Hourly upload and N3 · Energy (simulated day) ---

void test_f3_n3_one_day_gives_24_uploads() {
    Station station;
    station.clock.time = at(0, 0, kWakeDelayS);
    station.clock.lastSet = station.clock.time;
    station.wake();
    for (int i = 1; i < 96; ++i) {
        station.wakeAtNextAlarm();
    }

    TEST_ASSERT_EQUAL(96, station.storage.rows.size());
    TEST_ASSERT_EQUAL(24, station.log.count("connect"));
    TEST_ASSERT_EQUAL(96, station.power.sleepCount);
    // The last upload, at 23:00, sent every row stored before it, once:
    // 00:00 to 23:00 is 93 rows
    TEST_ASSERT_EQUAL(93, station.receivedRows().size());
}

// --- F3 · Hourly upload: content of the requests ---

void test_f3_upload_sends_the_new_rows_once() {
    Station station;
    station.clock.time = at(13, 45, kWakeDelayS);
    station.wake();  // no upload at 13:45
    station.wakeAtNextAlarm();  // 14:00:03: upload

    TEST_ASSERT_EQUAL(1, station.network.requests.size());
    const std::string& request = station.network.requests[0];
    TEST_ASSERT_EQUAL(0, request.find(std::string(kCsvHeader) + "\r\n"));

    std::vector<std::string> rows = station.receivedRows();
    TEST_ASSERT_EQUAL(2, rows.size());
    TEST_ASSERT_EQUAL_STRING("2026-10-01T13:45:03Z,1,18.40,62.00,1013.20",
                             rows[0].c_str());
    TEST_ASSERT_EQUAL_STRING("2026-10-01T14:00:03Z,1,18.40,62.00,1013.20",
                             rows[1].c_str());
    // Everything was acknowledged: the cursor is at the end
    TEST_ASSERT_EQUAL(station.storage.csv.size(), station.storage.cursor);
}

void test_n1_server_error_keeps_rows_for_next_upload() {
    Station station;
    station.network.serverWorks = false;
    station.wake();  // 14:00:03: the server refuses

    TEST_ASSERT_EQUAL(1, station.log.count("send"));
    TEST_ASSERT_EQUAL(0, station.storage.cursor);

    station.network.serverWorks = true;
    for (int i = 0; i < 4; ++i) {
        station.wakeAtNextAlarm();  // 14:15, 14:30, 14:45, 15:00
    }
    // The row of 14:00 was sent at 15:00, with the four new ones
    std::vector<std::string> rows = station.receivedRows();
    TEST_ASSERT_EQUAL(5, rows.size());
    TEST_ASSERT_EQUAL_STRING("2026-10-01T14:00:03Z,1,18.40,62.00,1013.20",
                             rows[0].c_str());
}

void test_large_backlog_is_sent_in_several_requests() {
    Station station;
    // 600 rows of about 45 bytes waiting, as after a week without Wi-Fi
    Record record;
    record.timeValid = true;
    record.values = station.sensor.read();
    for (int i = 0; i < 600; ++i) {
        record.timestamp = at(0, 0, 0) - 600 * 900 + i * 900;
        station.storage.append(record);
    }
    station.wake();  // 14:00:03: upload

    TEST_ASSERT_GREATER_THAN(1, station.network.requests.size());
    for (const std::string& request : station.network.requests) {
        TEST_ASSERT_LESS_OR_EQUAL(24 * 1024, request.size());
    }
    TEST_ASSERT_EQUAL(601, station.receivedRows().size());
    TEST_ASSERT_EQUAL(station.storage.csv.size(), station.storage.cursor);
}

// --- F4 · Daily time sync (three simulated days) ---

void test_f4_three_days_give_3_syncs_on_upload_connections() {
    Station station;
    station.clock.time = at(0, 0, kWakeDelayS);
    station.clock.lastSet = 0;  // e.g. first boot
    station.wake();
    for (int i = 1; i < 3 * 96; ++i) {
        station.wakeAtNextAlarm();
    }

    TEST_ASSERT_EQUAL(3, station.log.count("ntp"));
    TEST_ASSERT_EQUAL(0, station.log.count("ntp-while-disconnected"));
    // Syncs reuse the hourly connections: no extra connection
    TEST_ASSERT_EQUAL(3 * 24, station.log.count("connect"));
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_quarter_hour_wake_up_only_measures);
    RUN_TEST(test_full_hour_wake_up_uploads);
    RUN_TEST(test_button_wake_up_runs_maintenance_then_measures);
    RUN_TEST(test_f1_alarm_on_grid_and_in_the_future);
    RUN_TEST(test_f2_row_stored_before_any_network_call);
    RUN_TEST(test_f6_rows_flagged_until_ntp_succeeds);
    RUN_TEST(test_n1_wifi_down_at_full_hour);
    RUN_TEST(test_n1_ntp_down_keeps_schedule);
    RUN_TEST(test_n1_sensor_missing_row_still_stored);
    RUN_TEST(test_n1_storage_failure_keeps_schedule);
    RUN_TEST(test_n2_rtc_alarm_and_safety_timer_armed);
    RUN_TEST(test_n2_rtc_failure_safety_timer_only);
    RUN_TEST(test_f3_n3_one_day_gives_24_uploads);
    RUN_TEST(test_f4_three_days_give_3_syncs_on_upload_connections);
    RUN_TEST(test_f3_upload_sends_the_new_rows_once);
    RUN_TEST(test_n1_server_error_keeps_rows_for_next_upload);
    RUN_TEST(test_large_backlog_is_sent_in_several_requests);
    return UNITY_END();
}
