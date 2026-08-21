#include "WeatherStationFSM.h"

WeatherStationFSM::WeatherStationFSM() {
    _currentState = State::BOOT;
}

void WeatherStationFSM::execute() {
    // The main FSM loop. Runs until it reaches DEEP_SLEEP, then halts the CPU.
    while (_currentState != State::DEEP_SLEEP) {
        switch (_currentState) {
            case State::BOOT:
                handleBoot();
                break;
            case State::DATA_LOGGER:
                handleDataLogger();
                break;
            case State::WIFI_SYNC:
                handleWiFiSync();
                break;
            case State::FALLBACK_SERVER:
                handleFallbackServer();
                break;
            default:
                _currentState = State::DEEP_SLEEP;
                break;
        }
    }
    
    // Final state
    handleDeepSleep();
}

void WeatherStationFSM::handleBoot() {
    Serial.println("\n--- System Boot ---");
    
    // Always initialize RTC first to see if we have valid time
    _rtc.begin();
    
    esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
    
    if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT1) {
        // Fallback Button pressed!
        _currentState = State::FALLBACK_SERVER;
    } else {
        // Normal RTC Alarm (EXT0) or Undefined (Power On)
        _currentState = State::DATA_LOGGER;
    }
}

void WeatherStationFSM::handleDataLogger() {
    Serial.println("State: DATA_LOGGER");
    
    _sensors.begin();
    
    String timestamp = _rtc.getISOTimestamp();
    SensorData data = _sensors.takeReadings(timestamp);
    
    _sd.logData(data);
    
    // Check if it's time for the Daily Sync
    int currentHour = _rtc.getCurrentHour();
    
    // Simple logic: if it's the sync hour, we sync. 
    // In a production system, we'd check a flag to ensure it only happens ONCE during that hour.
    // For now, if we wake up at 2:00 AM, we sync.
    if (currentHour == WIFI_SYNC_HOUR) {
        Serial.println("Daily Sync Hour reached. Transitioning to WIFI_SYNC...");
        _currentState = State::WIFI_SYNC;
    } else {
        Serial.println("Log complete. Transitioning to DEEP_SLEEP...");
        _currentState = State::DEEP_SLEEP;
    }
}

void WeatherStationFSM::handleWiFiSync() {
    Serial.println("State: WIFI_SYNC");
    
    if (_wifi.connect()) {
        _uploader.uploadCSV(_sd);
        _rtc.syncNTP();
        _wifi.disconnect();
    }
    
    _currentState = State::DEEP_SLEEP;
}

void WeatherStationFSM::handleFallbackServer() {
    Serial.println("State: FALLBACK_SERVER");
    
    _server.start(_sd);
    
    // 3 Minute blocking loop
    unsigned long startTime = millis();
    unsigned long lastPrintTime = millis();
    unsigned long elapsed = 0;
    
    while (elapsed < AP_TIMEOUT_MS) {
        elapsed = millis() - startTime;
        
        if (millis() - lastPrintTime >= 10000) {
            lastPrintTime = millis();
            int remainingSeconds = (AP_TIMEOUT_MS - elapsed) / 1000;
            Serial.printf("AP Mode shutting down in %d seconds...\n", remainingSeconds);
        }
        
        delay(10); // Small yield
    }
    
    Serial.println("\nAP Timeout reached. Shutting down...");
    _server.stop(_sd);
    
    _currentState = State::DEEP_SLEEP;
}

void WeatherStationFSM::handleDeepSleep() {
    Serial.println("State: DEEP_SLEEP");
    
    // Set next alarm for exactly on the grid
    _rtc.setNextAlarm();
    
    esp_sleep_enable_ext0_wakeup((gpio_num_t)RTC_WAKEUP_PIN, 0);
    esp_sleep_enable_ext1_wakeup(1ULL << FALLBACK_BUTTON_PIN, ESP_EXT1_WAKEUP_ANY_HIGH);
    
    Serial.println("Entering Deep Sleep...");
    Serial.flush();
    
    // This halts the CPU. The script ends here!
    esp_deep_sleep_start();
}
