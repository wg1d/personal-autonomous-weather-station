/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/StateMachine.h
 *
 * Description:
 * The state machine run once per wake-up, from BOOT to SLEEP. It only
 * talks to the hardware through the interfaces of lib/ports, so the
 * same code runs on the board and in the tests.
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <cstddef>
#include <cstdint>

#include "Config.h"
#include "IClock.h"
#include "IMaintenance.h"
#include "INetwork.h"
#include "IPower.h"
#include "ISensor.h"
#include "IStorage.h"
#include "Record.h"
#include "Transitions.h"

/**
 * @brief The implementations the state machine works with.
 *
 * Hardware adapters on the board, test doubles in the tests.
 */
struct Ports {
    IClock& clock;              ///< Time and alarms
    ISensor& sensor;            ///< Values of the row
    IStorage& storage;          ///< Where the rows are kept
    INetwork& network;          ///< Wi-Fi, server and NTP
    IPower& power;              ///< Wake-up cause and deep sleep
    IMaintenance& maintenance;  ///< Access point session
};

/**
 * @brief What must survive deep sleep between two wake-ups.
 *
 * On the board, main.cpp keeps it in RTC memory (RTC_DATA_ATTR); in the
 * tests, the fixture keeps it between two simulated wake-ups.
 */
struct RetainedState {
    uint32_t lastSyncTime = 0;  ///< Time of the last NTP sync, 0 if none
};

/**
 * @brief The state machine run once per wake-up, from BOOT to SLEEP.
 *
 * Each state does its work, and sets the Conditions it can know. The
 * next state is then given by nextState() (Transitions.h).
 * The machine only talks to the outside world through the interfaces
 * given in Ports, and always reaches SLEEP: failures are handled inside
 * the states.
 */
class StateMachine {
public:
    /// Function called when a state is entered, for example to print it
    using StateListener = void (*)(State state);

    /**
     * @brief Creates the machine. It keeps references to its arguments.
     *
     * @param[in] config The settings of the core.
     * @param[in] ports The implementations of the interfaces.
     * @param[in,out] retained What survives deep sleep: read, and updated
     *                after a successful NTP sync.
     */
    StateMachine(const Config& config, Ports ports,
                 RetainedState& retained);

    /**
     * @brief Sets the function called at each state change.
     *
     * @param[in] listener The function, or nullptr for none.
     */
    void setListener(StateListener listener) { listener_ = listener; }

    /**
     * @brief Runs one wake-up, from BOOT to SLEEP.
     *
     * On the board, it never returns, since SLEEP enters deep sleep.
     */
    void run();

    /// Maximum number of states visited by one run
    static constexpr size_t kMaxVisited = 8;

    /**
     * @brief Number of states visited by the last run.
     *
     * @return The number of states, at most kMaxVisited.
     */
    size_t visitedCount() const { return visitedCount_; }

    /**
     * @brief A state visited by the last run, in order.
     *
     * @param[in] index Position in the path, below visitedCount().
     * @return The state visited at this position.
     */
    State visited(size_t index) const { return visited_[index]; }

private:
    // The work of each state
    void onBoot();
    void onMaintenance();
    void onMeasure();
    void onStore();
    void onUpload();
    void onTimeSync();
    void onSchedule();
    void onSleep();

    void enter(State state);
    void doWork(State state);

    const Config& config_;
    Ports ports_;
    RetainedState& retained_;
    StateListener listener_ = nullptr;

    // Context of the current wake-up only
    Conditions conditions_;
    bool clockValid_ = false;
    Record record_;
    SleepPlan plan_;

    State visited_[kMaxVisited] = {};
    size_t visitedCount_ = 0;
};
