#include <Arduino.h>
#include "WeatherStationFSM.h"

// The Orchestrator
WeatherStationFSM fsm;

void setup() {
    Serial.begin(115200);
    
    // The FSM execute() method runs the entire lifecycle sequentially
    // based on the wakeup cause. It blocks until it reaches the DEEP_SLEEP
    // state, where it halts the CPU. It never returns from execute().
    fsm.execute();
}

void loop() {
    // Empty. In a deep-sleep paradigm, loop() is never reached.
}
