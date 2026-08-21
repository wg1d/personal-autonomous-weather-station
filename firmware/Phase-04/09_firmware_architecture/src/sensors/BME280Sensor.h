#ifndef BME280SENSOR_H
#define BME280SENSOR_H

#include <Adafruit_BME280.h>
#include <Arduino.h>

/**
 * @class BME280Sensor
 * @brief Wrapper for the Adafruit BME280 temperature, humidity, and pressure sensor.
 */
class BME280Sensor {
public:
    BME280Sensor();
    
    /**
     * @brief Initializes the sensor on the I2C bus.
     * @return true if successfully found.
     */
    bool begin();
    
    float readTemperature();
    float readHumidity();
    float readPressure();

private:
    Adafruit_BME280 _bme;
};

#endif // BME280SENSOR_H
