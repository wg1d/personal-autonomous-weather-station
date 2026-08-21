#include "SensorManager.h"

SensorManager::SensorManager() {}

bool SensorManager::begin() {
    bool success = true;
    
    if (!_bme280.begin()) {
        Serial.println("Error: Could not find a valid BME280 sensor, check wiring!");
        success = false;
    }
    
    // Initialize other sensors here in the future
    
    return success;
}

SensorData SensorManager::takeReadings(const String& timestamp) {
    SensorData data;
    data.timestamp = timestamp;
    
    data.temperature = _bme280.readTemperature();
    data.humidity = _bme280.readHumidity();
    data.pressure = _bme280.readPressure();
    
    // Read other sensors here in the future
    
    return data;
}
