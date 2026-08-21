#ifndef SENSORMANAGER_H
#define SENSORMANAGER_H

#include <Arduino.h>
#include "BME280Sensor.h"

/**
 * @struct SensorData
 * @brief Unified structure holding all sensor readings.
 */
struct SensorData {
    String timestamp;
    float temperature;
    float humidity;
    float pressure;
    // Easy to add more fields here later (e.g., float uvIndex;)
};

/**
 * @class SensorManager
 * @brief Manages all connected sensors and returns unified readings.
 */
class SensorManager {
public:
    SensorManager();
    
    /**
     * @brief Initializes all connected sensors.
     * @return true if all critical sensors are found.
     */
    bool begin();
    
    /**
     * @brief Queries all sensors and populates the SensorData struct.
     * @param timestamp The current ISO 8601 timestamp from the RTC.
     * @return A populated SensorData structure.
     */
    SensorData takeReadings(const String& timestamp);

private:
    BME280Sensor _bme280;
};

#endif // SENSORMANAGER_H
