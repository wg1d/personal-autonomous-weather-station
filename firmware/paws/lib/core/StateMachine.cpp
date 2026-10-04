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

#include <cstdio>

#include "CsvFormat.h"
#include "Rules.h"

// Text of one upload request: for the measurements, the header line, then
// at most about 500 rows of 45 bytes (see the Upload Protocol); for the
// log, up to 24 KB of lines. It is static: reserved once
// when the firmware is built, instead of on the stack of the ESP32, which
// is only 8 KB.
static char batch[24 * 1024];

StateMachine::StateMachine(const Config& config, Ports ports)
    : config_(config), ports_(ports) {}

void StateMachine::run() {
    conditions_ = Conditions{};

    State current = State::Boot;
    while (true) {
        // Report the state: printed on the board, checked by the tests
        ports_.log.stateEntered(stateName(current));

        // Do the work of the state. It also reads the inputs that this
        // state handles (wake-up cause, Wi-Fi connection...) and sets the
        // matching conditions.
        doWork(current);
        if (current == State::Sleep) {
            return;  // final state
        }

        // Choose the next state from the conditions
        State next = nextState(current, conditions_);
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
    // next try
    conditions_.connected = ports_.network.connect(config_.wifiTimeoutS);
    if (conditions_.connected) {
        // The measurements first: they matter more than the log
        sendUnsent(DataKind::Measurements);
        sendUnsent(DataKind::Log);
    }
    conditions_.syncNeeded = isSyncNeeded(ports_.clock.now(), clockValid_,
                                     ports_.clock.lastSetTime(), config_);
}

void StateMachine::sendUnsent(DataKind kind) {
    // Each request of measurements starts with the header line, so that
    // it describes itself (see the Upload Protocol). The log has none.
    size_t headerLength = 0;
    if (kind == DataKind::Measurements) {
        headerLength = snprintf(batch, sizeof(batch), "%s\r\n", kCsvHeader);
    }

    while (true) {
        size_t linesLength = ports_.storage.readUnsent(
            kind, batch + headerLength, sizeof(batch) - headerLength);
        if (linesLength == 0) {
            return;  // everything was sent, or the storage cannot be read
        }
        if (!ports_.network.send(kind, batch, headerLength + linesLength)) {
            return;  // the same lines will be sent at the next upload
        }
        // The cursor only moves once the server confirmed (N1)
        if (!ports_.storage.markSent(kind, linesLength)) {
            return;
        }
    }
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
    ports_.storage.close();
    ports_.power.sleep(plan_);
}
