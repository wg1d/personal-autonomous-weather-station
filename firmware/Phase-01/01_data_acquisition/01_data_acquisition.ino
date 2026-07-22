/*
 * Project: Personal Autonomous Weather Station
 * Phase 01: Data Acquisition
 * File: 01_data_acquisition.ino
 * 
 * Description:
 * This sketch initializes the BME280 sensor and continuously reads 
 * the temperature, humidity, and atmospheric pressure. 
 * The data is printed to the Serial Monitor every 5 seconds.
 * 
 * Wiring (ESP32 Wrover -> BME280):
 * - 3V3 -> VIN
 * - GND -> GND
 * - Pin 21 -> SDA
 * - Pin 22 -> SCL
 * 
 * Dependencies:
 * - Adafruit BME280 Library
 * - Adafruit Unified Sensor Library
 */

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

Adafruit_BME280 bme; // Create a BME280 object

void setup() {
  Serial.begin(115200);
  Serial.println("BME280 Initialization Test");

  // Initialize the BME280 sensor using default I2C pins (SDA=21, SCL=22)
  // The default I2C address for most BME280 modules is 0x76 (sometimes 0x77)
  if (!bme.begin(0x76)) {
    Serial.println("Could not find a valid BME280 sensor, check wiring!");
    while (1); // Halt if sensor not found
  }
}

void loop() {
  // Read data from the sensor
  float temperature = bme.readTemperature(); // In Celsius
  float humidity = bme.readHumidity();       // In %
  float pressure = bme.readPressure() / 100.0F; // In hPa

  // Print the results to the terminal
  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println(" *C");

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");

  Serial.print("Pressure: ");
  Serial.print(pressure);
  Serial.println(" hPa");

  Serial.println("-------------------------");

  // Wait for 5 seconds before taking the next reading
  delay(5000); 
}
