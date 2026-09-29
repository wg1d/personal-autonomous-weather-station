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
    station.retained.lastSyncTime = 0;  // sync needed
    station.network.ntpAvailable = false;
    station.wake();

    TEST_ASSERT_EQUAL(1, station.storage.rows.size());
    TEST_ASSERT_EQUAL(0, station.clock.setTimeCount);
    TEST_ASSERT_EQUAL_UINT32(0, station.retained.lastSyncTime);
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
    station.retained.lastSyncTime = station.clock.time;
    station.wake();
    for (int i = 1; i < 96; ++i) {
        station.wakeAtNextAlarm();
    }

    TEST_ASSERT_EQUAL(96, station.storage.rows.size());
    TEST_ASSERT_EQUAL(24, station.log.count("connect"));
    TEST_ASSERT_EQUAL(96, station.power.sleepCount);
}

// --- F4 · Daily time sync (three simulated days) ---

void test_f4_three_days_give_3_syncs_on_upload_connections() {
    Station station;
    station.clock.time = at(0, 0, kWakeDelayS);
    station.retained.lastSyncTime = 0;  // e.g. first boot
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
    return UNITY_END();
}
