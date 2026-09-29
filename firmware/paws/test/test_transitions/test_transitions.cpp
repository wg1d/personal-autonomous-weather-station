/*
 * Project: Personal Autonomous Weather Station
 * File: test/test_transitions/test_transitions.cpp
 *
 * Description:
 * Unit tests of the transitions (lib/core/Transitions.h): one test per
 * row of the transitions table of the design chapter.
 *
 * Dependencies: lib/core, Unity.
 */

#include <unity.h>

#include "Transitions.h"

void setUp() {}
void tearDown() {}

// Checks nextState(), with the state names in the failure message
void assertNext(State expected, State current, const Conditions& conditions) {
    TEST_ASSERT_EQUAL_STRING(stateName(expected),
                             stateName(nextState(current, conditions)));
}

void test_boot_to_maintenance_when_woken_by_button() {
    Conditions conditions;
    conditions.wokenByButton = true;
    assertNext(State::Maintenance, State::Boot, conditions);
}

void test_boot_to_measure_otherwise() {
    assertNext(State::Measure, State::Boot, Conditions{});
}

void test_maintenance_to_measure() {
    assertNext(State::Measure, State::Maintenance, Conditions{});
}

void test_measure_to_store() {
    assertNext(State::Store, State::Measure, Conditions{});
}

void test_store_to_upload_when_upload_needed() {
    Conditions conditions;
    conditions.uploadNeeded = true;
    assertNext(State::Upload, State::Store, conditions);
}

void test_store_to_schedule_when_no_upload_needed() {
    assertNext(State::Schedule, State::Store, Conditions{});
}

void test_upload_to_time_sync_when_connected_and_sync_needed() {
    Conditions conditions;
    conditions.connected = true;
    conditions.syncNeeded = true;
    assertNext(State::TimeSync, State::Upload, conditions);
}

void test_upload_to_schedule_in_every_other_case() {
    Conditions conditions;
    conditions.connected = true;  // no sync needed
    assertNext(State::Schedule, State::Upload, conditions);

    conditions.connected = false;  // no Wi-Fi, sync needed
    conditions.syncNeeded = true;
    assertNext(State::Schedule, State::Upload, conditions);

    conditions.syncNeeded = false;  // no Wi-Fi, no sync needed
    assertNext(State::Schedule, State::Upload, conditions);
}

void test_time_sync_to_schedule() {
    assertNext(State::Schedule, State::TimeSync, Conditions{});
}

void test_schedule_to_sleep() {
    assertNext(State::Sleep, State::Schedule, Conditions{});
}

void test_sleep_is_final() {
    assertNext(State::Sleep, State::Sleep, Conditions{});
}

// N2: a loop in the transitions would keep the station awake until the
// battery is empty. Every combination of conditions must lead from BOOT
// to SLEEP, in at most 7 steps (the longest path goes through all the
// 8 states).
void test_every_path_reaches_sleep() {
    const int kMaxSteps = 7;
    for (int bits = 0; bits < 16; ++bits) {
        Conditions conditions;
        conditions.wokenByButton = bits & 1;
        conditions.uploadNeeded = bits & 2;
        conditions.connected = bits & 4;
        conditions.syncNeeded = bits & 8;

        State state = State::Boot;
        int steps = 0;
        while (state != State::Sleep && steps < kMaxSteps) {
            state = nextState(state, conditions);
            ++steps;
        }
        TEST_ASSERT_EQUAL_STRING_MESSAGE("SLEEP", stateName(state),
                                         "loop in the transitions");
    }
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_boot_to_maintenance_when_woken_by_button);
    RUN_TEST(test_boot_to_measure_otherwise);
    RUN_TEST(test_maintenance_to_measure);
    RUN_TEST(test_measure_to_store);
    RUN_TEST(test_store_to_upload_when_upload_needed);
    RUN_TEST(test_store_to_schedule_when_no_upload_needed);
    RUN_TEST(test_upload_to_time_sync_when_connected_and_sync_needed);
    RUN_TEST(test_upload_to_schedule_in_every_other_case);
    RUN_TEST(test_time_sync_to_schedule);
    RUN_TEST(test_schedule_to_sleep);
    RUN_TEST(test_sleep_is_final);
    RUN_TEST(test_every_path_reaches_sleep);
    return UNITY_END();
}
