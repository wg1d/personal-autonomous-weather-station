#include "BME280Sensor.h"

BME280Sensor::BME280Sensor() {}

bool BME280Sensor::begin() {
    return _bme.begin(0x76);
}

float BME280Sensor::readTemperature() {
    return _bme.readTemperature();
}

float BME280Sensor::readHumidity() {
    return _bme.readHumidity();
}

float BME280Sensor::readPressure() {
    return _bme.readPressure() / 100.0F; // Convert Pa to hPa
}
