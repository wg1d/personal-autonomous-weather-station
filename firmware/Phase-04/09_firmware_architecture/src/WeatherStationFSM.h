#ifndef WEATHERSTATIONFSM_H
#define WEATHERSTATIONFSM_H

#include <Arduino.h>
#include "config.h"

// The Specialists (Drivers)
#include "sensors/SensorManager.h"
#include "storage/SDManager.h"
#include "time/RTCManager.h"
#include "network/WiFiConnection.h"
#include "network/TelemetryUploader.h"
#include "network/FallbackServer.h"

/**
 * @enum State
 * @brief Represents all possible states of the weather station.
 */
enum class State {
    BOOT,             
    DATA_LOGGER,      
    WIFI_SYNC,        
    FALLBACK_SERVER,  
    DEEP_SLEEP        
};

/**
 * @class WeatherStationFSM
 * @brief The Finite State Machine (The Orchestrator) that dictates the ESP32 lifecycle.
 */
class WeatherStationFSM {
public:
    WeatherStationFSM();
    
    /**
     * @brief Evaluates the wake reason and runs the corresponding sequence.
     * Ends by halting the CPU in deep sleep.
     */
    void execute();

private:
    State _currentState;
    
    // The Specialists
    SensorManager _sensors;
    SDManager _sd;
    RTCManager _rtc;
    WiFiConnection _wifi;
    TelemetryUploader _uploader;
    FallbackServer _server;

    // State Handlers
    void handleBoot();
    void handleDataLogger();
    void handleWiFiSync();
    void handleFallbackServer();
    void handleDeepSleep();
};

#endif // WEATHERSTATIONFSM_H
