/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/Transitions.cpp
 *
 * Description:
 * Implementation of the transitions (see Transitions.h). Each case reads
 * like one or two rows of the transitions table of the Phase 4 design.
 *
 * Dependencies: none (standard C++ only).
 */

#include "Transitions.h"

const char* stateName(State state) {
    switch (state) {
        case State::Boot:        return "BOOT";
        case State::Maintenance: return "MAINTENANCE";
        case State::Measure:     return "MEASURE";
        case State::Store:       return "STORE";
        case State::Upload:      return "UPLOAD";
        case State::TimeSync:    return "TIME_SYNC";
        case State::Schedule:    return "SCHEDULE";
        case State::Sleep:       return "SLEEP";
    }
    return "?";
}

State nextState(State current, const Conditions& conditions) {
    switch (current) {
        case State::Boot:
            if (conditions.wokenByButton) {
                return State::Maintenance;
            }
            // RTC alarm, safety timer and power-on are handled the same way
            return State::Measure;

        case State::Maintenance:
            // An alarm may have fired during the session: take a reading
            // anyway, SCHEDULE then realigns the station on the grid
            return State::Measure;

        case State::Measure:
            return State::Store;

        case State::Store:
            if (conditions.uploadNeeded) {
                return State::Upload;
            }
            return State::Schedule;

        case State::Upload:
            if (conditions.connected && conditions.syncNeeded) {
                // Reuse the open connection (F4)
                return State::TimeSync;
            }
            // No Wi-Fi, or no sync needed
            return State::Schedule;

        case State::TimeSync:
            return State::Schedule;

        case State::Schedule:
            return State::Sleep;

        case State::Sleep:
            return State::Sleep;
    }
    return State::Sleep;
}
