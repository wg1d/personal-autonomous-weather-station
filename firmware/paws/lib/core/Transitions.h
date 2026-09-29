/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/Transitions.h
 *
 * Description:
 * The states of the machine and its transitions, as one pure function:
 * the code version of the transitions table of the Phase 4 design.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

/**
 * @brief The states of the machine (see the Phase 4 design).
 */
enum class State {
    Boot,         ///< Read the wake-up cause and the clock status
    Maintenance,  ///< Run the access point session
    Measure,      ///< Read all the sensors
    Store,        ///< Append the row to the storage
    Upload,       ///< Connect to the Wi-Fi and send the rows
    TimeSync,     ///< Correct the clock with NTP
    Schedule,     ///< Program the next alarm and the safety timer
    Sleep,        ///< Arm the wake-up sources and sleep
};

/**
 * @brief Name of a state, for the logs.
 *
 * @param[in] state A state.
 * @return Its name in capitals, as in the Phase 4 design ("BOOT"...).
 */
const char* stateName(State state);

/**
 * @brief The conditions the transitions depend on.
 *
 * They are the "Condition" column of the transitions table in the design
 * chapter. Each state sets the conditions it can know, during the
 * current wake-up; nextState() only reads them.
 */
struct Conditions {
    bool wokenByButton = false;  ///< Set by BOOT
    bool uploadNeeded = false;   ///< Set by STORE
    bool connected = false;      ///< Set by UPLOAD
    bool syncNeeded = false;     ///< Set by UPLOAD
};

/**
 * @brief The state that follows the current one.
 *
 * @param[in] current The state that just did its work.
 * @param[in] conditions The conditions set during this wake-up.
 * @return The next state. SLEEP is final: it returns SLEEP.
 */
State nextState(State current, const Conditions& conditions);
