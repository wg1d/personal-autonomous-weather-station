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

#include <cstdint>

#include "Config.h"
#include "IClock.h"
#include "ILog.h"
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
 * Groups the references to the seven interfaces, so that the
 * constructor of the machine takes a single argument. On the board, they
 * are the hardware adapters; in the tests, the test doubles.
 */
struct Ports {
    IClock& clock;              ///< Time and alarms
    ISensor& sensor;            ///< Values of the row
    IStorage& storage;          ///< Where the rows are kept
    INetwork& network;          ///< Wi-Fi, server and NTP
    IPower& power;              ///< Wake-up cause and deep sleep
    IMaintenance& maintenance;  ///< Access point session
    ILog& log;                  ///< Where the states entered are reported
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
    /**
     * @brief Creates the machine.
     *
     * @param[in] config The settings of the core.
     * @param[in] ports The implementations of the interfaces.
     */
    StateMachine(const Config& config, Ports ports);

    /**
     * @brief Runs one wake-up, from BOOT to SLEEP.
     *
     * On the board, it never returns, since SLEEP enters deep sleep.
     */
    void run();

private:
    // Calls the on...() function of a state
    void doWork(State state);

    // The work of each state
    void onBoot();
    void onMaintenance();
    void onMeasure();
    void onStore();
    void onUpload();
    void sendUnsent(DataKind kind);  // part of UPLOAD, while connected
    void onTimeSync();
    void onSchedule();
    void onSleep();

    const Config& config_;
    Ports ports_;

    // What the states of the current wake-up pass to each other
    Conditions conditions_;  // read by nextState()
    bool clockValid_ = false;
    Record record_;          // filled by MEASURE, stored by STORE
    SleepPlan plan_;         // filled by SCHEDULE, used by SLEEP
};
