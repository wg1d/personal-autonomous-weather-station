/*
 * Project: Personal Autonomous Weather Station
 * File: lib/core/StateMachine.cpp
 *
 * Description:
 * Implementation of the state machine. Each state does its work and
 * records what it found out; nextState() then chooses the next state.
 * Failures are handled inside the states: the machine always reaches
 * SLEEP.
 *
 * Dependencies: none (standard C++ only).
 */

#include "StateMachine.h"

#include "Rules.h"

StateMachine::StateMachine(const Config& config, Ports ports)
    : config_(config), ports_(ports) {}

void StateMachine::run() {
    conditions_ = Conditions{};

    State current = State::Boot;
    while (true) {
        // Report the state: printed on the board, checked by the tests
        ports_.log.stateEntered(stateName(current));

        // Actions of the current state. They also read the inputs of the
        // machine (wake-up cause, Wi-Fi connected...) and set the matching
        // conditions: an input is only known once its state has acted.
        doWork(current);
        if (current == State::Sleep) {
            return;  // final state
        }

        // Evolution: choose the next state from the conditions
        State next = nextState(current, conditions_);

        // This machine has no action on transitions: all the actions
        // belong to the states

        current = next;
    }
}

void StateMachine::doWork(State state) {
    switch (state) {
        case State::Boot:        onBoot(); break;
        case State::Maintenance: onMaintenance(); break;
        case State::Measure:     onMeasure(); break;
        case State::Store:       onStore(); break;
        case State::Upload:      onUpload(); break;
        case State::TimeSync:    onTimeSync(); break;
        case State::Schedule:    onSchedule(); break;
        case State::Sleep:       onSleep(); break;
    }
}

void StateMachine::onBoot() {
    clockValid_ = ports_.clock.isValid();
    conditions_.wokenByButton = ports_.power.wakeCause() == WakeCause::Button;
}

void StateMachine::onMaintenance() {
    ports_.maintenance.run(config_.maintenanceDurationS);
}

void StateMachine::onMeasure() {
    record_.timestamp = ports_.clock.now();
    record_.timeValid = clockValid_;
    record_.values = ports_.sensor.read();
}

void StateMachine::onStore() {
    // A failed write is reported by the adapter; the schedule continues
    // (N1), since stopping would lose the next measurements too
    ports_.storage.append(record_);
    conditions_.uploadNeeded =
        isUploadNeeded(record_.timestamp, clockValid_, config_);
}

void StateMachine::onUpload() {
    // On failure, nothing is sent: the rows stay on the SD card for the
    // next try. Sending the rows after the upload cursor comes in A4.
    conditions_.connected = ports_.network.connect(config_.wifiTimeoutS);
    conditions_.syncNeeded = isSyncNeeded(ports_.clock.now(), clockValid_,
                                     ports_.clock.lastSetTime(), config_);
}

void StateMachine::onTimeSync() {
    uint32_t unixTime = 0;
    if (ports_.network.fetchTime(unixTime, config_.ntpTimeoutS)) {
        ports_.clock.setTime(unixTime);
        clockValid_ = true;
    }
    // On failure, the next upload tries again
}

void StateMachine::onSchedule() {
    // The connection stays open from UPLOAD to here, so that TIME_SYNC
    // can reuse it (F4): close it before sleeping
    if (conditions_.connected) {
        ports_.network.disconnect();
    }

    // Read the time again: the upload may have taken several seconds, and
    // an alarm computed from an older time could be in the past
    uint32_t now = ports_.clock.now();
    uint32_t alarm = nextAlarm(now, config_);
    bool alarmSet = ports_.clock.setAlarm(alarm);

    plan_.rtcAlarm = alarmSet;
    plan_.button = true;
    plan_.timerSeconds = safetyTimerSeconds(now, alarm, alarmSet, config_);
}

void StateMachine::onSleep() {
    ports_.power.sleep(plan_);
}
